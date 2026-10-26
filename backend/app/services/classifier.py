import logging
import re
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

# Civic Department Categories
CIVIC_CATEGORIES = [
    "Roads & Infrastructure",
    "Sanitation & Solid Waste",
    "Water Supply & Sewage",
    "Electricity & Street Lighting",
    "Public Health & Environment",
]

DEPARTMENT_MAP = {
    "Roads & Infrastructure": "ROADS",
    "Sanitation & Solid Waste": "SANITATION",
    "Water Supply & Sewage": "WATER",
    "Electricity & Street Lighting": "POWER",
    "Public Health & Environment": "HEALTH",
}

# High-priority keywords that indicate urgent civic danger
CRITICAL_KEYWORDS = [
    "spark", "live wire", "explosion", "electrocution", "flood", "flooding",
    "collapse", "cylinder", "fire", "toxic", "poisonous", "danger", "fatal",
    "gushing", "sinkhole", "accident"
]

HIGH_PRIORITY_KEYWORDS = [
    "overflow", "burst", "deep pothole", "dengue", "malaria", "blackout",
    "darkness", "pitch black", "open manhole", "sewage leak", "choked", "stray dog attack"
]


class ComplaintClassifier:
    """
    Intelligent complaint text classification using Hugging Face pipelines
    with keyword-assisted urgency scoring and robust fallback.
    """

    def __init__(self):
        self.pipeline = None
        self._initialized = False

    def _lazy_init(self):
        if self._initialized:
            return
        try:
            from transformers import pipeline
            # Using zero-shot classification with BART-MNLI or distilbart
            # Using valhalla/distilbart-mnli-12-3 or facebook/bart-large-mnli
            self.pipeline = pipeline(
                "zero-shot-classification",
                model="valhalla/distilbart-mnli-12-3",
                device=-1,  # CPU by default
            )
            logger.info("Hugging Face Zero-Shot Classifier initialized successfully.")
        except Exception as e:
            logger.warning(
                f"Could not load Hugging Face pipeline ({e}). Operating in resilient heuristic mode."
            )
            self.pipeline = None
        finally:
            self._initialized = True

    def _heuristic_classify(self, text: str) -> Dict[str, Any]:
        """
        Fast, offline keyword matching fallback if Hugging Face model is loading or unavailable.
        """
        lower = text.lower()
        scores = {cat: 0.1 for cat in CIVIC_CATEGORIES}

        # Roads
        if any(w in lower for w in ["road", "pothole", "footpath", "bridge", "asphalt", "speed breaker", "crater"]):
            scores["Roads & Infrastructure"] += 0.8
        # Sanitation
        if any(w in lower for w in ["garbage", "trash", "waste", "dump", "bin", "litter", "cleaning", "sweeping", "dead animal"]):
            scores["Sanitation & Solid Waste"] += 0.8
        # Water
        if any(w in lower for w in ["water", "pipe", "pipeline", "leak", "tap", "sewage", "drainage", "drain", "dirty water", "drinking"]):
            scores["Water Supply & Sewage"] += 0.8
        # Electricity
        if any(w in lower for w in ["light", "streetlight", "electric", "pole", "wire", "power", "meter", "dark", "transformer"]):
            scores["Electricity & Street Lighting"] += 0.8
        # Health
        if any(w in lower for w in ["mosquito", "dengue", "health", "hospital", "stray", "foul", "disease", "hygiene", "smoke"]):
            scores["Public Health & Environment"] += 0.8

        best_cat = max(scores, key=scores.get)
        confidence = min(0.95, scores[best_cat])
        if confidence == 0.1:
            best_cat = "Roads & Infrastructure"
            confidence = 0.50

        return {"category": best_cat, "confidence": round(confidence, 2)}

    def calculate_priority(self, text: str) -> Dict[str, Any]:
        """
        Calculates urgency level based on civic safety risk factors.
        """
        lower = text.lower()
        score = 0.3  # Base Medium score

        for word in CRITICAL_KEYWORDS:
            if re.search(rf"\b{re.escape(word)}\b", lower):
                score += 0.45
                break

        for word in HIGH_PRIORITY_KEYWORDS:
            if re.search(rf"\b{re.escape(word)}\b", lower):
                score += 0.25
                break

        score = min(1.0, max(0.1, score))

        if score >= 0.75:
            priority = "CRITICAL"
        elif score >= 0.55:
            priority = "HIGH"
        elif score >= 0.35:
            priority = "MEDIUM"
        else:
            priority = "LOW"

        return {"priority": priority, "priority_score": round(score, 2)}

    def classify(self, title: str, description: str) -> Dict[str, Any]:
        """
        Classifies complaint title + description into a category, calculates confidence,
        computes priority, and recommends the target department.
        """
        combined_text = f"{title}. {description}".strip()
        self._lazy_init()

        category = None
        confidence = 0.85

        if self.pipeline:
            try:
                res = self.pipeline(combined_text, candidate_labels=CIVIC_CATEGORIES)
                category = res["labels"][0]
                confidence = round(float(res["scores"][0]), 2)
            except Exception as e:
                logger.error(f"Error executing HF classification: {e}")
                heur = self._heuristic_classify(combined_text)
                category = heur["category"]
                confidence = heur["confidence"]
        else:
            heur = self._heuristic_classify(combined_text)
            category = heur["category"]
            confidence = heur["confidence"]

        priority_info = self.calculate_priority(combined_text)
        dept_code = DEPARTMENT_MAP.get(category, "ROADS")

        return {
            "category": category,
            "confidence": confidence,
            "priority": priority_info["priority"],
            "priority_score": priority_info["priority_score"],
            "suggested_department_code": dept_code,
        }


classifier_service = ComplaintClassifier()

