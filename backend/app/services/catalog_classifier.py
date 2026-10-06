"""Two-stage, building-aware retrieval-augmented campus service classifier."""
import asyncio
import json
import logging
import re
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.gemini_rate_limit import wait_for_gemini_slot
from app.prompts import PROMPT_VERSION, build_catalog_prompt
from app.services.duplicate_detector import _cosine_similarity, generate_embedding, generate_embeddings

logger = logging.getLogger(__name__)
settings = get_settings()
DATA_DIR = Path(__file__).resolve().parents[1] / "data"
CATALOG_PATH = DATA_DIR / "service_catalog.json"
EMBEDDINGS_PATH = DATA_DIR / "service_catalog_embeddings.json"
TOP_K = 6
_embedding_lock = asyncio.Lock()


class CatalogClassification(BaseModel):
    candidate_id: Optional[str] = None
    is_campus_related: bool = True
    intent: Literal["hazard", "service_request"]
    severity: Optional[int] = Field(default=None, ge=1, le=5)
    is_safety_critical: bool = False
    summary: str
    reasoning: str
    intent_confidence: float = Field(ge=0, le=1)
    group_confidence: float = Field(ge=0, le=1)
    subcategory_confidence: float = Field(ge=0, le=1)


def load_catalog() -> list[dict]:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def _entry_text(entry: dict) -> str:
    return " ".join([
        entry["group"], entry["subcategory"], *entry.get("keywords", []),
    ])


def _tokens(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", (value or "").lower()))


def _keyword_score(query: str, entry: dict) -> float:
    query_lower = (query or "").lower()
    query_tokens = _tokens(query_lower)
    terms = [entry["group"], entry["subcategory"], *entry.get("keywords", [])]
    score = 0.0
    for term in terms:
        term_lower = term.lower().strip()
        if term_lower and term_lower in query_lower:
            score += 1.0 + 0.15 * len(_tokens(term_lower))
        term_tokens = _tokens(term_lower)
        if term_tokens:
            score += 0.25 * len(query_tokens & term_tokens) / len(term_tokens)
    return min(1.0, score / 4.0)


def _building_adjustment(score: float, building_type: str, entry: dict) -> float:
    applicable = {value.lower() for value in entry.get("applicable_building_types", [])}
    if not building_type or not applicable or building_type == "campus_wide":
        return score
    if building_type.lower() in applicable:
        return min(1.0, score + 0.20)
    return max(0.0, score - 0.08)


async def _catalog_vectors(catalog: list[dict]) -> dict[str, list[float]]:
    catalog_ids = [entry["id"] for entry in catalog]
    if EMBEDDINGS_PATH.exists():
        try:
            cached = json.loads(EMBEDDINGS_PATH.read_text(encoding="utf-8"))
            if (
                cached.get("model") == settings.embedding_model
                and cached.get("catalog_ids") == catalog_ids
                and set(cached.get("vectors", {})) == set(catalog_ids)
            ):
                return cached.get("vectors", {})
        except (OSError, ValueError, TypeError):
            logger.warning("Ignoring invalid catalog embedding cache")
    if not settings.gemini_api_key:
        return {}

    async with _embedding_lock:
        if EMBEDDINGS_PATH.exists():
            try:
                cached = json.loads(EMBEDDINGS_PATH.read_text(encoding="utf-8"))
                if (
                    cached.get("model") == settings.embedding_model
                    and cached.get("catalog_ids") == catalog_ids
                    and set(cached.get("vectors", {})) == set(catalog_ids)
                ):
                    return cached.get("vectors", {})
            except (OSError, ValueError, TypeError):
                pass
        texts = [_entry_text(entry) for entry in catalog]
        vectors = await generate_embeddings(texts)
        result = {entry["id"]: vector for entry, vector in zip(catalog, vectors) if vector}
        if result:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            EMBEDDINGS_PATH.write_text(json.dumps({"model": settings.embedding_model, "catalog_ids": catalog_ids, "vectors": result}), encoding="utf-8")
        return result


async def retrieve_candidates(
    text: str,
    building_type: str = "",
    top_k: int = TOP_K,
    catalog: Optional[list[dict]] = None,
) -> list[dict]:
    catalog = catalog or load_catalog()
    vectors = await _catalog_vectors(catalog)
    query_vector = await generate_embedding(text) if settings.gemini_api_key and vectors else None
    scored = []
    for entry in catalog:
        if query_vector and entry["id"] in vectors:
            score = _cosine_similarity(query_vector, vectors[entry["id"]])
        else:
            score = _keyword_score(text, entry)
        score = _building_adjustment(score, building_type, entry)
        scored.append((score, entry))
    scored.sort(key=lambda pair: (pair[0], pair[1]["id"]), reverse=True)
    return [dict(entry, retrieval_score=round(score, 4)) for score, entry in scored[:top_k]]


def _fallback_result(text: str, candidates: list[dict], reason: str = "Gemini API unavailable") -> dict:
    selected = candidates[0] if candidates else None
    score = selected.get("retrieval_score", 0.0) if selected else 0.0
    confidence = min(0.5, max(0.15, score))
    related = bool(selected and score >= 0.12)
    intent = selected["intent"] if related else "hazard"
    service_request = intent == "service_request"
    severity = None if service_request else (selected.get("default_severity") if selected else 2)
    return {
        "candidate_id": selected["id"] if related else None,
        "catalog_id": selected["id"] if related else None,
        "is_campus_related": related,
        "intent": intent,
        "severity": severity,
        "is_safety_critical": False,
        "summary": selected["subcategory"] if related else "Campus report needs review",
        "reasoning": "Matched with catalog keywords/embeddings because Gemini classification was unavailable.",
        "intent_confidence": confidence,
        "group_confidence": confidence,
        "subcategory_confidence": confidence,
        "confidence": confidence,
        "service_group": selected["group"] if related else None,
        "service_subcategory": selected["subcategory"] if related else None,
        "owner_department": selected["owner_department"] if related else "Admin",
        "default_severity": selected.get("default_severity") if related else None,
        "sla_hours": selected.get("sla_hours") if related else None,
        "prompt_version": PROMPT_VERSION,
        "candidates": [],
        "fallback": True,
        "fallback_reason": reason,
    }


def _validate_candidate(result: CatalogClassification, candidates: list[dict]) -> CatalogClassification:
    candidate_ids = {candidate["id"] for candidate in candidates}
    if result.is_campus_related and result.candidate_id not in candidate_ids:
        raise ValueError("Gemini selected a catalog id outside the retrieved candidates")
    if not result.is_campus_related:
        result.candidate_id = None
        result.is_safety_critical = False
        result.severity = None
    else:
        chosen = next(candidate for candidate in candidates if candidate["id"] == result.candidate_id)
        result.intent = chosen["intent"]
        if result.intent == "service_request":
            result.severity = None
            result.is_safety_critical = False
        elif result.severity is None:
            result.severity = chosen.get("default_severity") or 2
    return result


async def classify_with_candidate_list(
    image_path: Optional[str],
    text: str,
    building: str,
    zone: str,
    building_type: str,
    candidates: list[dict],
    prompt: Optional[str] = None,
) -> dict:
    """Run stage two against exactly the supplied candidate list."""
    if not settings.gemini_api_key:
        return _fallback_result(text, candidates, "GEMINI_API_KEY is not configured")
    from google import genai
    from google.genai import types
    from PIL import Image

    prompt = prompt or build_catalog_prompt(text, building, zone, building_type or "unknown", candidates)
    contents: list = [prompt]
    if image_path:
        try:
            contents.append(Image.open(image_path))
        except (OSError, ValueError):
            logger.warning("Unable to read report image for catalog classification")
    client = genai.Client(api_key=settings.gemini_api_key)

    def generate(prompt_text: str):
        wait_for_gemini_slot()
        return client.models.generate_content(
            model=settings.gemini_model,
            contents=[prompt_text, *contents[1:]],
            config=types.GenerateContentConfig(
                temperature=0,
                response_mime_type="application/json",
                response_schema=CatalogClassification,
            ),
        )

    try:
        response = await asyncio.to_thread(generate, prompt)
        try:
            result = CatalogClassification.model_validate_json(response.text or "")
        except Exception:
            response = await asyncio.to_thread(generate, prompt + "\nReturn one valid JSON object matching the schema exactly.")
            result = CatalogClassification.model_validate_json(response.text or "")
        result = _validate_candidate(result, candidates)
        chosen = next((candidate for candidate in candidates if candidate["id"] == result.candidate_id), None)
        data = result.model_dump()
        if chosen:
            data.update({
                "service_group": chosen["group"],
                "service_subcategory": chosen["subcategory"],
                "owner_department": chosen["owner_department"],
                "catalog_id": chosen["id"],
                "sla_hours": chosen["sla_hours"],
                "default_severity": chosen["default_severity"],
            })
        else:
            data.update({"service_group": None, "service_subcategory": None, "owner_department": "Admin", "catalog_id": None, "sla_hours": None})
        data["confidence"] = round((result.intent_confidence + result.group_confidence + result.subcategory_confidence) / 3, 4)
        data["prompt_version"] = PROMPT_VERSION
        data["fallback"] = False
        data["candidates"] = confirmation_candidates(result, candidates)
        return data
    except Exception as exc:
        logger.warning("Catalog Gemini classification failed; using fallback: %s", exc)
        return _fallback_result(text, candidates, str(exc))


def confirmation_candidates(result: CatalogClassification, candidates: list[dict]) -> list[dict]:
    if result.subcategory_confidence < 0.6 <= result.group_confidence:
        return candidates[:3]
    return []


async def classify_catalog_report(
    image_path: Optional[str],
    text: str,
    building: str,
    zone: str = "",
    building_type: str = "",
) -> dict:
    """Retrieve six building-aware catalog entries, then classify with Gemini."""
    candidates = await retrieve_candidates(text, building_type)
    if not settings.gemini_api_key:
        logger.warning("No GEMINI_API_KEY set; using catalog fallback")
        return _fallback_result(text, candidates, "GEMINI_API_KEY is not configured")
    return await classify_with_candidate_list(
        image_path, text, building, zone, building_type, candidates
    )


def map_to_legacy_fields(result: dict) -> dict:
    """Map catalog results onto the original four categories and hazard types."""
    group = (result.get("service_group") or "").lower()
    subcategory = (result.get("service_subcategory") or "").lower()
    text = f"{group} {subcategory}"
    if not result.get("is_campus_related", True):
        return {"category": "other", "hazard_type": "other"}
    if "electr" in text or "power" in text or "lighting" in text or "hvac" in text:
        category = "electrical"
    elif "security" in text or "cctv" in text or "access control" in text:
        category = "security"
    elif any(word in text for word in ["civil", "plumb", "fire", "housekeeping", "waste", "pest", "sanitation", "maintenance"]):
        category = "civil"
    else:
        category = "other"
    if "electric" in text or "wiring" in text or "power supply" in text:
        hazard_type = "exposed_wiring"
    elif "fire" in text or "smoke" in text:
        hazard_type = "fire_risk"
    elif "plumb" in text or "leak" in text or "drain" in text or "water supply" in text:
        hazard_type = "water_leakage"
    elif "security" in text or "cctv" in text or "emergency response" in text:
        hazard_type = "suspicious_activity"
    elif "waste" in text or "housekeeping" in text or "pest" in text or "clean" in text:
        hazard_type = "sanitation"
    elif "lighting" in text:
        hazard_type = "broken_light"
    elif result.get("intent") == "service_request":
        hazard_type = "other"
    else:
        hazard_type = "broken_infrastructure"
    return {"category": category, "hazard_type": hazard_type}
