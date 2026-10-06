"""
Duplicate detection and recurrence tracking using Gemini embeddings + cosine similarity.
"""
import json
import logging
import math
from datetime import datetime, timedelta
from typing import Optional, List

import numpy as np
from sqlalchemy.orm import Session

from app.models import Report, ReportStatus
from app.core.config import get_settings
from app.core.gemini_rate_limit import wait_for_gemini_slot

logger = logging.getLogger(__name__)
settings = get_settings()

DUPLICATE_THRESHOLD = 0.85
POSSIBLE_THRESHOLD = 0.70
RECURRENCE_THRESHOLD = 0.80
RECURRENCE_DAYS = 90


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    a_arr = np.array(a, dtype=np.float32)
    b_arr = np.array(b, dtype=np.float32)
    norm_a = np.linalg.norm(a_arr)
    norm_b = np.linalg.norm(b_arr)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a_arr, b_arr) / (norm_a * norm_b))


def _haversine_distance(lat1, lng1, lat2, lng2) -> float:
    """Distance in meters between two GPS coordinates."""
    R = 6371000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


async def generate_embedding(text: str) -> Optional[List[float]]:
    """Generate a text embedding using Gemini embedding model."""
    if not settings.gemini_api_key:
        logger.warning("No GEMINI_API_KEY — embedding generation skipped")
        return None
    try:
        from google import genai
        client = genai.Client(api_key=settings.gemini_api_key)
        wait_for_gemini_slot()
        result = client.models.embed_content(
            model=settings.embedding_model,
            contents=f"task: semantic similarity | text: {text}",
        )
        return result.embeddings[0].values if result.embeddings else None
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        return None


async def generate_embeddings(texts: List[str]) -> List[Optional[List[float]]]:
    """Embed multiple independent texts in one catalog initialization request."""
    if not settings.gemini_api_key:
        logger.warning("No GEMINI_API_KEY — embedding generation skipped")
        return [None] * len(texts)
    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=settings.gemini_api_key)
        embeddings = []
        for offset in range(0, len(texts), 80):
            contents = [
                types.Content(parts=[types.Part.from_text(text=f"task: semantic similarity | text: {text}")])
                for text in texts[offset:offset + 80]
            ]
            wait_for_gemini_slot()
            result = client.models.embed_content(
                model=settings.embedding_model,
                contents=contents,
            )
            embeddings.extend(item.values for item in (result.embeddings or []))
        return embeddings
    except Exception as e:
        logger.error(f"Batch embedding generation failed: {e}")
        return [None] * len(texts)


def _embedding_text(report: Report) -> str:
    """Build the text used for embedding from report fields."""
    parts = [
        report.hazard_type or "",
        report.ai_summary or report.title or "",
        report.description or "",
        report.building or "",
        report.zone or "",
    ]
    return " ".join(p for p in parts if p).strip()


async def compute_and_store_embedding(report: Report, db: Session) -> None:
    """Generate embedding for a report and persist it."""
    text = _embedding_text(report)
    embedding = await generate_embedding(text)
    if embedding:
        report.embedding = json.dumps(embedding)
        db.commit()


def _get_embedding(report: Report) -> Optional[List[float]]:
    if not report.embedding:
        return None
    try:
        return json.loads(report.embedding)
    except Exception:
        return None


async def find_similar(new_report: Report, db: Session) -> dict:
    """
    Find similar open reports to detect duplicates or recurring issues.
    Returns:
      { status: DUPLICATE|POSSIBLE_DUPLICATE|RECURRING|UNIQUE,
        duplicate_of: int|None,
        suggestions: [...],
        recurrence_count: int,
        message: str|None }
    """
    new_embedding = _get_embedding(new_report)

    # ── Candidate selection: same building first ──────────────────────────────
    candidates = db.query(Report).filter(
        Report.building == new_report.building,
        Report.id != new_report.id,
    ).all()

    # If GPS available, filter to ~100m radius
    if new_report.lat and new_report.lng:
        candidates = [
            r for r in candidates
            if not (r.lat and r.lng)
            or _haversine_distance(new_report.lat, new_report.lng, r.lat, r.lng) <= 100
        ]

    # ── Embedding-based similarity ────────────────────────────────────────────
    scored: List[tuple] = []  # (similarity, report)

    for candidate in candidates:
        emb = _get_embedding(candidate)
        if emb and new_embedding:
            sim = _cosine_similarity(new_embedding, emb)
        else:
            # Fallback: simple keyword overlap
            words_new = set(_embedding_text(new_report).lower().split())
            words_cand = set(_embedding_text(candidate).lower().split())
            overlap = len(words_new & words_cand)
            union = len(words_new | words_cand)
            sim = overlap / union if union else 0.0
        scored.append((sim, candidate))

    scored.sort(key=lambda x: x[0], reverse=True)

    # ── Check for DUPLICATE (open reports) ────────────────────────────────────
    open_statuses = [
        ReportStatus.reported, ReportStatus.assigned,
        ReportStatus.in_progress, ReportStatus.pending_confirmation,
        ReportStatus.reopened
    ]

    for sim, candidate in scored:
        if candidate.status not in open_statuses:
            continue
        if sim >= DUPLICATE_THRESHOLD:
            return {
                "status": "DUPLICATE",
                "duplicate_of": candidate.id,
                "suggestions": [],
                "recurrence_count": 0,
                "message": (
                    f"A similar issue already exists (#{candidate.id}: {candidate.title}). "
                    "Your report was merged and the original has been hyped."
                ),
            }

    # ── Check for POSSIBLE_DUPLICATE ─────────────────────────────────────────
    suggestions = []
    for sim, candidate in scored:
        if candidate.status not in open_statuses:
            continue
        if POSSIBLE_THRESHOLD <= sim < DUPLICATE_THRESHOLD:
            suggestions.append({
                "id": candidate.id,
                "title": candidate.title,
                "building": candidate.building,
                "zone": candidate.zone,
                "similarity": round(sim, 3),
                "hype_count": candidate.hype_count,
            })
        if len(suggestions) >= 3:
            break

    # ── Recurrence check (resolved reports within 90 days) ───────────────────
    cutoff = datetime.utcnow() - timedelta(days=RECURRENCE_DAYS)
    recurrence_count = 0

    for sim, candidate in scored:
        if candidate.status == ReportStatus.resolved and candidate.resolved_at:
            if candidate.resolved_at >= cutoff and sim >= RECURRENCE_THRESHOLD:
                recurrence_count = (candidate.recurrence_count or 0) + 1
                break

    if suggestions:
        return {
            "status": "POSSIBLE_DUPLICATE",
            "duplicate_of": None,
            "suggestions": suggestions,
            "recurrence_count": recurrence_count,
            "message": f"Found {len(suggestions)} possibly similar open report(s) in this area.",
        }

    if recurrence_count > 0:
        return {
            "status": "RECURRING",
            "duplicate_of": None,
            "suggestions": [],
            "recurrence_count": recurrence_count,
            "message": "This appears to be a recurring issue at this location.",
        }

    return {
        "status": "UNIQUE",
        "duplicate_of": None,
        "suggestions": [],
        "recurrence_count": 0,
        "message": None,
    }
