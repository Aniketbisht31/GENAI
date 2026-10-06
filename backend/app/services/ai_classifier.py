"""
AI Classifier using Gemini multimodal API.
classify_report(image_path, text) -> dict with hazard analysis.
"""
import json
import re
import os
import logging
import asyncio
from typing import Optional
from pydantic import BaseModel, validator

from PIL import Image

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# ── Pydantic schema for AI output ─────────────────────────────────────────────

VALID_HAZARD_TYPES = {
    "exposed_wiring", "water_leakage", "broken_infrastructure",
    "fire_risk", "unsafe_structure", "pothole", "broken_light",
    "suspicious_activity", "sanitation", "other", "not_a_hazard"
}

VALID_CATEGORIES = {"electrical", "civil", "security", "other"}


class ClassificationResult(BaseModel):
    hazard_type: str
    category: str
    severity: int
    is_safety_critical: bool
    summary: str
    reasoning: str
    confidence: float

    @validator("severity")
    def severity_range(cls, v):
        return max(1, min(5, v))

    @validator("confidence")
    def confidence_range(cls, v):
        return max(0.0, min(1.0, v))

    @validator("hazard_type")
    def valid_hazard(cls, v):
        return v if v in VALID_HAZARD_TYPES else "other"

    @validator("category")
    def valid_category(cls, v):
        return v if v in VALID_CATEGORIES else "other"


# ── System prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a campus safety hazard classifier for a university.
Analyze the provided image and/or text description and return ONLY a valid JSON object.

SEVERITY SCALE (1-5):
1 - Minor: Small cosmetic issues (e.g., chipped paint, loose door handle)
2 - Low: Inconvenient but not dangerous (e.g., flickering light, small pothole)
3 - Moderate: Could cause injury if ignored (e.g., wet floor, broken step, water leakage)
4 - High: Likely to cause injury (e.g., exposed wiring, large structural crack, broken glass)
5 - Critical: Immediate danger to life (e.g., live wire sparking, structural collapse, fire, violence)

SAFETY-CRITICAL (is_safety_critical = true):
- Fire or smoke detected
- Exposed live electrical wires
- Structural collapse or imminent fall risk
- Suspicious activity, weapons, or violence
- Any severity 5 hazard

HAZARD TYPES:
- exposed_wiring: Electrical wires exposed, sparking, or damaged
- water_leakage: Leaks, flooding, burst pipes
- broken_infrastructure: Broken steps, glass, railings, doors, furniture
- fire_risk: Smoke, fire, flammable materials improperly stored
- unsafe_structure: Cracks, ceilings, walls, floor collapse risk
- pothole: Road or path damage
- broken_light: Non-functional or broken lighting
- suspicious_activity: Suspicious persons, packages, behavior
- sanitation: Garbage overflow, sewage, pest infestation
- other: Does not fit above categories
- not_a_hazard: Selfie, meme, landscape, food, personal photos, or clearly not a safety hazard

CATEGORIES:
- electrical: Power, wiring, lighting issues
- civil: Infrastructure, roads, structural, sanitation
- security: Suspicious activity, safety, access control
- other: Does not fit electrical/civil/security

RULES:
- If the image/text is NOT a campus hazard (selfie, meme, random photo), return not_a_hazard
- Be conservative: when in doubt, assign higher severity
- Confidence should reflect how certain you are (0.0 to 1.0)

Return ONLY this JSON, no markdown, no explanation:
{
  "hazard_type": "<type>",
  "category": "<category>",
  "severity": <1-5>,
  "is_safety_critical": <true|false>,
  "summary": "<one-line title under 10 words>",
  "reasoning": "<2-3 sentence justification>",
  "confidence": <0.0-1.0>
}"""


# ── Keyword fallback ──────────────────────────────────────────────────────────

KEYWORD_RULES = [
    (["wire", "electric", "shock", "sparking", "electri"], "exposed_wiring", "electrical", 4, True),
    (["fire", "smoke", "burn", "flame", "blaze"], "fire_risk", "civil", 5, True),
    (["leak", "flood", "water", "pipe", "burst"], "water_leakage", "civil", 3, False),
    (["crack", "collapse", "structural", "ceiling", "wall fall"], "unsafe_structure", "civil", 4, True),
    (["broken", "smash", "shatter", "glass", "step"], "broken_infrastructure", "civil", 3, False),
    (["pothole", "road", "path", "pavement"], "pothole", "civil", 2, False),
    (["light", "dark", "bulb", "lamp"], "broken_light", "civil", 2, False),
    (["suspicious", "weapon", "fight", "threat", "stalker"], "suspicious_activity", "security", 4, True),
    (["garbage", "waste", "sewage", "pest", "rat", "cockroach"], "sanitation", "civil", 2, False),
]


def _keyword_classify(text: str) -> dict:
    text_lower = text.lower()
    for keywords, hazard_type, category, severity, critical in KEYWORD_RULES:
        if any(kw in text_lower for kw in keywords):
            return {
                "hazard_type": hazard_type,
                "category": category,
                "severity": severity,
                "is_safety_critical": critical,
                "summary": f"Possible {hazard_type.replace('_', ' ')} detected",
                "reasoning": "Classified by keyword matching (AI unavailable).",
                "confidence": 0.5,
            }
    return {
        "hazard_type": "other",
        "category": "other",
        "severity": 2,
        "is_safety_critical": False,
        "summary": "Campus hazard reported",
        "reasoning": "Could not determine hazard type automatically.",
        "confidence": 0.3,
    }


def _extract_json(text: str) -> Optional[dict]:
    """Extract JSON from model response, handling markdown code blocks."""
    # Strip markdown code blocks
    text = re.sub(r"```(?:json)?", "", text).strip()
    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Try to find first {...} block
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return None


async def classify_report(image_path: Optional[str], text: str) -> dict:
    """
    Classify a hazard report using Gemini multimodal.
    Falls back to keyword classifier on API failure.
    Returns a dict matching ClassificationResult schema.
    """
    if not settings.gemini_api_key:
        logger.warning("No GEMINI_API_KEY set — using keyword classifier")
        return _keyword_classify(text)

    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=settings.gemini_api_key)
        parts = [SYSTEM_PROMPT]

        # Add image if provided
        if image_path and os.path.exists(image_path):
            img = Image.open(image_path)
            parts.append(img)

        # Add text description
        if text:
            parts.append(f"\nReport description: {text}")
        elif not image_path:
            return _keyword_classify("")

        def generate(content):
            return client.models.generate_content(
                model=settings.gemini_model,
                contents=content,
                config=types.GenerateContentConfig(
                    temperature=0,
                    response_mime_type="application/json",
                    response_schema=ClassificationResult,
                ),
            )

        response = await asyncio.to_thread(generate, parts)
        raw = response.text or ""

        data = _extract_json(raw)
        if data is None:
            # Retry once
            logger.warning("Malformed JSON from Gemini, retrying...")
            response = await asyncio.to_thread(generate, parts + ["\nReturn ONLY valid JSON, no other text."])
            data = _extract_json(response.text or "")

        if data is None:
            logger.error("Gemini returned non-JSON twice, falling back to keywords")
            return _keyword_classify(text)

        # Validate with Pydantic
        result = ClassificationResult(**data)
        return result.dict()

    except Exception as e:
        logger.error(f"Gemini API error: {e}. Falling back to keyword classifier.")
        return _keyword_classify(text)
