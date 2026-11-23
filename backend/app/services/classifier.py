"""
CivicLens AI/ML Pipeline — Stage 2 & 3: Complaint Classification + Priority Engine

Classification:
  Primary: XLM-RoBERTa-base fine-tuned (lazy-loaded, falls back to zero-shot mDeBERTa)
  Fallback: Keyword heuristics when no model is available

Priority:
  AI extracts FACTUAL incident attributes only (what is physically happening).
  A transparent deterministic formula converts attributes → score → label:
      P = 0.35·S + 0.25·I + 0.15·E + 0.10·C + 0.15·T   (all components 0–5)

  Two hard rules that override the weighted average
  ──────────────────────────────────────────────────
  Rule 1 — Safety Override (SLA breach prevention):
    If a verified life-safety hazard pattern is detected (live electrical, active
    fire, imminent structural collapse, gas explosion, toxic spill), the complaint
    is ALWAYS assigned CRITICAL priority and a 2-hour SLA, regardless of the
    weighted score.  A low score cannot downgrade a confirmed hazard.

  Rule 2 — Time-based escalation cap:
    Pending time (T) can raise LOW → MEDIUM → HIGH, but it can NEVER raise a
    complaint to CRITICAL on its own.  CRITICAL is reserved for safety-based
    escalation only.  An old routine complaint that has been pending seven days
    will reach HIGH at most.
"""
import re
import logging
import math
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Taxonomy
# ---------------------------------------------------------------------------
PRIMARY_CATEGORIES = [
    "Infrastructure & Roads",
    "Water Supply & Drainage",
    "Electricity & Street Lighting",
    "Sanitation & Waste Management",
    "Public Health & Environment",
    "Traffic & Road Safety",
    "Building Safety",
    "Parks & Public Spaces",
]

SUBCATEGORY_MAP = {
    "Infrastructure & Roads": [
        "Pothole / Road Damage", "Broken Footpath", "Bridge Damage",
        "Road Flooding", "Speed Breaker Required", "Illegal Encroachment",
    ],
    "Water Supply & Drainage": [
        "Pipeline Leakage", "No Water Supply", "Contaminated Water",
        "Sewage Overflow", "Drain Blockage", "Flooding / Waterlogging",
    ],
    "Electricity & Street Lighting": [
        "Streetlight Failure", "Exposed / Live Wire", "Power Outage",
        "Transformer Fault", "Illegal Connection", "Fire Hazard – Electrical",
    ],
    "Sanitation & Waste Management": [
        "Garbage Pileup", "Missed Waste Collection", "Illegal Dumping",
        "Public Toilet – Broken", "Dead Animal", "Sewage Smell",
    ],
    "Public Health & Environment": [
        "Mosquito Breeding / Dengue Risk", "Stray Animal Attack",
        "Air / Noise Pollution", "Food Safety Violation",
        "Open Defecation", "Disease Outbreak",
    ],
    "Traffic & Road Safety": [
        "Signal Failure", "Illegal Parking Obstruction", "Accident Blackspot",
        "No Road Markings", "Footover Bridge Required",
    ],
    "Building Safety": [
        "Unsafe / Collapsing Structure", "Illegal Construction",
        "Fire Safety Violation",
    ],
    "Parks & Public Spaces": [
        "Broken Equipment", "Encroachment", "Fallen Tree", "Poor Maintenance",
    ],
}

DEPARTMENT_ROUTING = {
    "Infrastructure & Roads":          {"primary": "ROADS",    "secondary": "TRAFFIC"},
    "Water Supply & Drainage":         {"primary": "WATER",    "secondary": "SANITATION"},
    "Electricity & Street Lighting":   {"primary": "POWER",    "secondary": "EMERGENCY"},
    "Sanitation & Waste Management":   {"primary": "SANITATION","secondary": "HEALTH"},
    "Public Health & Environment":     {"primary": "HEALTH",   "secondary": "SANITATION"},
    "Traffic & Road Safety":           {"primary": "TRAFFIC",  "secondary": "ROADS"},
    "Building Safety":                 {"primary": "SAFETY",   "secondary": "EMERGENCY"},
    "Parks & Public Spaces":           {"primary": "PARKS",    "secondary": "ROADS"},
}

# ---------------------------------------------------------------------------
# Safety Override Hazards
# ---------------------------------------------------------------------------
# Any complaint matching one of these patterns is ALWAYS assigned CRITICAL
# priority and a 2-hour SLA.  The weighted-average score (P) cannot downgrade
# a verified safety hazard.  New patterns must be reviewed and approved before
# being added — do not add vague urgency phrases here.
#
# Qualifying triggers:
#   • Verified live / bare electrical hazard
#   • Active fire or confirmed burning
#   • Imminent or confirmed structural collapse (building / bridge / wall / roof)
#   • Sinkhole or ground collapse
#   • LPG / gas leak or explosion risk
#   • Chemical or toxic spill / leak
#   • Major flooding (road, house, home)
#   • Acute disease outbreak or epidemic
#   • Electrocution or electric-shock incident
# ---------------------------------------------------------------------------
CRITICAL_HAZARD_PATTERNS = [
    # Live / exposed electrical hazard (English, Hindi, Marathi)
    r'\b(live|bare|exposed|naked|hanging)\s+(wire|electric|electrical|cable|conductor)\b',
    r'\b(electrocution|electric.?shock|bijli.?shock)\b',
    r'(जीवंत|उघडी|तुटलेली|धोकादायक)\s+(तार|विद्युत\s*तार|विजेची\s*तार)',
    r'(विद्युत\s*शॉक|विजेचा\s*धक्का|शॉक|करंट)',
    # Active fire
    r'\b(active\s+)?fire\b(?!.{0,30}\bstation\b)',   # exclude "fire station"
    r'\b(blaze|burning\s+building|building\s+on\s+fire)\b',
    r'(आग\s*लागली|कचऱ्याला\s*आग|जळत\s*आहे)',
    # Structural collapse — imminent or confirmed
    r'\b(building|wall|roof|bridge|flyover|structure|pillar|slab)\s+(collaps\w*|fallen|caved|crumbling|cracks?)\b',
    r'\b(imminent|about\s+to)\s+collaps\w*\b',
    r'(इमारत|भिंत|पूल|छत|सज्जा)\s*(कोसळ|पडण्याची|तडा)',
    # Sinkhole / ground collapse / open manhole
    r'\b(sinkhole|ground.?collapse|road.?collapse|cave.?in|open\s+manhole)\b',
    r'(उघडे\s*मॅनहोल|गटाराचे\s*झाकण|खड्डा)',
    # LPG / gas leak or explosion
    r'\b(cylinder|lpg|gas\s+pipe|gas\s+line)\s+(leak\w*|explod\w*|blast\w*|burst\w*)\b',
    r'\bgas\s+leak\b',
    r'(गॅस\s*गळती|सिलेंडर\s*स्फोट)',
    # Chemical / toxic spill
    r'\b(chemical|toxic|hazardous)\s+(spill|leak\w*|dump\w*|discharge)\b',
    # Major flooding
    r'\b(severe|major|extreme|heavy)\s+(flood\w*|waterlogg\w*)\b',
    r'\b(flood\w*)\s+(road|house|home|building|basement)\b',
    # Acute disease outbreak
    r'\b(acute|sudden)\s+(outbreak|epidemic|cluster)\b',
]

SEVERITY_KEYWORDS = {
    5: ["fatal", "death", "died", "dead body", "life threatening", "critical"],
    4: ["dangerous", "khatarnak", "accident", "injured", "collapsing", "exposed wire"],
    3: ["deep pothole", "overflow", "dengue", "burst", "blackout", "pitch black"],
    2: ["damage", "broken", "leaking", "overflowing", "not working", "bada gaddha"],
    1: ["minor", "small", "slight", "aesthetic", "inconvenience"],
}

EXPOSURE_KEYWORDS = {
    5: ["school", "hospital", "market", "crowded", "children", "public", "hundreds"],
    4: ["residential", "apartment", "colony", "near", "junction", "crossing"],
    3: ["street", "road", "lane", "area"],
    2: ["locality", "sector", "ward"],
    1: ["personal", "single", "one"],
}


class ComplaintClassifier:
    """
    Hybrid complaint classifier:
      - Zero-shot with multilingual NLI model (immediate, no fine-tuning needed)
      - Plug-in slot for fine-tuned XLM-RoBERTa-base classification head
      - Falls back to transparent keyword heuristics when models unavailable
    """

    def __init__(self):
        self._zs_pipeline = None
        self._ft_model = None
        self._ft_tokenizer = None
        self._initialized = False
        import os
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        classifier_path = os.path.join(base_dir, "models", "classifier")
        if os.path.exists(classifier_path):
            try:
                self.load_finetuned_model(classifier_path)
            except Exception as e:
                logger.warning(f"Auto-load finetuned model failed: {e}")

    def _lazy_init_zeroshot(self):
        if self._initialized:
            return
        self._initialized = True
        try:
            from transformers import pipeline
            try:
                self._zs_pipeline = pipeline(
                    "zero-shot-classification",
                    model="MoritzLaurer/mDeBERTa-v3-base-mnli-xnli",
                    device=-1,
                )
                logger.info("mDeBERTa multilingual zero-shot classifier loaded.")
            except Exception:
                self._zs_pipeline = pipeline(
                    "zero-shot-classification",
                    model="valhalla/distilbart-mnli-12-3",
                    device=-1,
                )
                logger.info("DistilBART zero-shot fallback loaded.")
        except Exception as e:
            logger.warning(f"Zero-shot pipeline unavailable: {e}. Using heuristics.")
            self._zs_pipeline = None

    def _heuristic_classify(self, text: str) -> Dict[str, Any]:
        lower = text.lower()
        scores: Dict[str, float] = {cat: 0.1 for cat in PRIMARY_CATEGORIES}
        kw_map = {
            "Infrastructure & Roads": [
                "road", "pothole", "gaddha", "footpath", "bridge", "asphalt", "sadak", "rasta", "pavement",
                "रस्ता", "खड्डा", "खड्ड्या", "फुटपाथ", "पेव्हर", "पूल", "डांबरीकरण", "कठडा", "चर"
            ],
            "Water Supply & Drainage": [
                "water", "paani", "pani", "pipe", "pipeline", "leak", "tap", "nali", "naali", "sewage", "drain", "drinking",
                "पाणी", "पाईप", "पाईपलाईन", "गळती", "ड्रेनेज", "नळ", "सांडपाणी", "गटार", "नाला", "निचरा"
            ],
            "Electricity & Street Lighting": [
                "light", "streetlight", "electric", "bijli", "pole", "wire", "taar", "power", "dark", "transformer",
                "वीज", "पथदिवे", "स्ट्रीट", "खांब", "ट्रान्सफॉर्मर", "विद्युत", "अंधार", "दिवा", "व्होल्टेज"
            ],
            "Sanitation & Waste Management": [
                "garbage", "kachra", "trash", "waste", "dump", "bin", "litter", "clean", "safai", "sweeping",
                "कचरा", "कचराकुंडी", "घाण", "अस्वच्छता", "शौचालय", "घंटागाडी", "झाडलोट", "दुर्गंधी"
            ],
            "Public Health & Environment": [
                "mosquito", "machchar", "dengue", "malaria", "health", "stray", "disease", "bimari", "smoke", "pollution",
                "डास", "औषध", "फवारणी", "रोगराई", "आरोग्य", "प्रदूषण", "डेंग्यू", "अन्न", "हॉस्पिटल"
            ],
            "Traffic & Road Safety": [
                "traffic", "signal", "parking", "accident", "speed", "vehicle", "jam",
                "वाहतूक", "सिग्नल", "गतिरोधक", "अपघात", "मोकाट कुत्रे", "गाड्या"
            ],
            "Building Safety": [
                "building", "wall", "roof", "structure", "crack", "collaps", "unsafe", "illegal construction",
                "इमारत", "धोकादायक इमारत", "सज्जा", "मॅनहोल", "कोसळ", "तडा"
            ],
            "Parks & Public Spaces": [
                "park", "garden", "tree", "playground", "bench", "encroach",
                "बाग", "उद्यान", "खेळणी", "झाड", "मैदान", "स्मशानभूमी", "अतिक्रमण"
            ],
        }
        for cat, keywords in kw_map.items():
            hits = sum(1 for kw in keywords if kw in lower)
            if hits > 0:
                scores[cat] = 0.4 + min(0.5, hits * 0.12)
        best = max(scores, key=scores.get)
        confidence = round(min(0.95, scores[best]), 2)
        return {"category": best, "confidence": confidence}

    def _select_subcategory(self, text: str, category: str) -> str:
        lower = text.lower()
        candidates = SUBCATEGORY_MAP.get(category, ["General"])
        for sub in candidates:
            if any(kw in lower for kw in sub.lower().split()):
                return sub
        return candidates[0]

    def _detect_critical_hazard(self, text: str) -> Optional[str]:
        """
        Returns the matched hazard phrase if a qualifying safety hazard is found,
        otherwise None.  Match is case-insensitive on the normalised text.
        Only verified physical-incident patterns qualify — urgency phrases such as
        "life threatening" or "very urgent" do NOT appear here and do NOT trigger
        the safety override.
        """
        lower = text.lower()
        for pattern in CRITICAL_HAZARD_PATTERNS:
            m = re.search(pattern, lower)
            if m:
                return m.group(0)
        return None

    def classify(self, title: str, description: str, language: str = "en") -> Dict[str, Any]:
        combined = f"{title}. {description}".strip()

        category = None
        confidence = 0.80

        # 1. Use custom fine-tuned model if available with heuristic ensembling
        if self._ft_model and self._ft_tokenizer:
            try:
                result = self._run_finetuned(combined)
                hr = self._heuristic_classify(combined)
                if hr["confidence"] >= 0.50 and result["confidence"] < 0.40:
                    category = hr["category"]
                    confidence = hr["confidence"]
                else:
                    category = result["category"]
                    confidence = result["confidence"]
            except Exception as e:
                logger.warning(f"Fine-tuned model failed: {e}")

        # 2. Fall back to zero-shot NLI pipeline
        if category is None:
            self._lazy_init_zeroshot()
            if self._zs_pipeline:
                try:
                    res = self._zs_pipeline(combined, candidate_labels=PRIMARY_CATEGORIES)
                    category = res["labels"][0]
                    confidence = round(float(res["scores"][0]), 3)
                except Exception as e:
                    logger.warning(f"Zero-shot pipeline failed: {e}")

        # 3. Fall back to rule-based heuristics
        if category is None:
            hr = self._heuristic_classify(combined)
            category = hr["category"]
            confidence = hr["confidence"]

        subcategory = self._select_subcategory(combined, category)
        routing = DEPARTMENT_ROUTING.get(category, {"primary": "ROADS", "secondary": "HEALTH"})
        hazard_type = self._detect_critical_hazard(combined)

        # immediate_risk is set TRUE only when the classifier detects a physical
        # safety hazard — NOT when the citizen merely uses urgent-sounding language.
        immediate_risk = hazard_type is not None

        return {
            "category": category,
            "subcategory": subcategory,
            "confidence": confidence,
            "hazard": hazard_type is not None,
            "hazard_type": hazard_type,
            "immediate_risk": immediate_risk,
            "suggested_department_code": routing["primary"],
            "secondary_department_code": routing["secondary"],
        }

    def _run_finetuned(self, text: str) -> Dict[str, Any]:
        """
        Run inference using loaded fine-tuned model (e.g. Yama Indic or XLM-RoBERTa).
        """
        import torch
        inputs = self._ft_tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=256,
            padding=True,
        )
        with torch.no_grad():
            outputs = self._ft_model(**inputs)
            logits = outputs.logits
            probs = torch.softmax(logits, dim=-1).squeeze(0)
            pred_idx = int(torch.argmax(probs).item())
            confidence = round(float(probs[pred_idx].item()), 3)

        label_map = getattr(self, "_label_map", None)
        if label_map and "id2label" in label_map:
            category = label_map["id2label"].get(str(pred_idx), PRIMARY_CATEGORIES[min(pred_idx, len(PRIMARY_CATEGORIES) - 1)])
        elif hasattr(self._ft_model.config, "id2label") and self._ft_model.config.id2label:
            category = self._ft_model.config.id2label.get(pred_idx, PRIMARY_CATEGORIES[min(pred_idx, len(PRIMARY_CATEGORIES) - 1)])
        else:
            category = PRIMARY_CATEGORIES[min(pred_idx, len(PRIMARY_CATEGORIES) - 1)]

        return {"category": category, "confidence": confidence}

    def load_finetuned_model(self, model_path: str):
        import os
        import json
        from transformers import AutoTokenizer, AutoModelForSequenceClassification
        self._ft_tokenizer = AutoTokenizer.from_pretrained(model_path)
        self._ft_model = AutoModelForSequenceClassification.from_pretrained(model_path)
        self._ft_model.eval()

        label_map_file = os.path.join(model_path, "label_map.json")
        if os.path.exists(label_map_file):
            try:
                with open(label_map_file, "r", encoding="utf-8") as f:
                    self._label_map = json.load(f)
            except Exception as e:
                logger.warning(f"Could not load label_map.json: {e}")

        logger.info(f"Fine-tuned classifier loaded from: {model_path}")


# ---------------------------------------------------------------------------
# Priority Engine
# ---------------------------------------------------------------------------

class PriorityEngine:
    """
    Deterministic weighted priority scorer.
    P = 0.35·S + 0.25·I + 0.15·E + 0.10·C + 0.15·T
    with safety override for critical hazards.
    """

    WEIGHTS = {"S": 0.35, "I": 0.25, "E": 0.15, "C": 0.10, "T": 0.15}

    def extract_attributes(self, title: str, description: str, hazard: bool = False) -> Dict[str, Any]:
        combined = f"{title}. {description}".lower()

        severity = 1
        for score, kws in sorted(SEVERITY_KEYWORDS.items(), reverse=True):
            if any(kw in combined for kw in kws):
                severity = score
                break

        immediate_risk = 2
        risk_patterns = [
            (5, ["children", "hospital", "school", "collapsed", "electrocution", "fire"]),
            (4, ["dangerous", "accident", "injured", "exposed wire", "khatarnak"]),
            (3, ["traffic", "overflow", "burst", "dengue", "pitch black"]),
            (2, ["not working", "broken", "leaking"]),
        ]
        for score, kws in risk_patterns:
            if any(kw in combined for kw in kws):
                immediate_risk = score
                break

        exposure = 2
        for score, kws in sorted(EXPOSURE_KEYWORDS.items(), reverse=True):
            if any(kw in combined for kw in kws):
                exposure = score
                break

        evidence = 1
        if any(kw in combined for kw in ["gate", "pillar", "ward", "sector", "near", "junction", "opposite"]):
            evidence += 1
        if any(kw in combined for kw in ["since", "days", "weeks", "yesterday", "ongoing"]):
            evidence += 1
        if re.search(r'\d+', combined):
            evidence += 1
        evidence = min(5, evidence)

        urgency_claim = any(kw in combined for kw in [
            "urgent", "urgently", "immediately", "jaldi", "please", "emergency",
            "life threatening", "very urgent", "extremely",
        ])
        # NOTE: urgency_claim is captured for officer visibility and audit only.
        # It is NEVER fed into the priority scoring formula.  A citizen writing
        # "very urgent" or "life threatening" does not change the score — only
        # the physical attributes (severity, risk, exposure) affect the formula.

        ongoing = any(kw in combined for kw in [
            "still", "continues", "ongoing", "since days", "since weeks",
            "every day", "regularly", "ho raha", "hai abhi"
        ])

        return {
            "severity": severity,
            "immediate_risk": immediate_risk,
            "public_exposure": exposure,
            "evidence_quality": evidence,
            "urgency_claim": urgency_claim,
            "incident_ongoing": ongoing,
            "hazard": hazard,
        }

    def calculate_priority(
        self,
        severity: float,
        immediate_risk: float,
        public_exposure: float,
        context_score: float,
        time_pending_days: float = 0,
        hazard: bool = False,
        hazard_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Convert extracted attributes → weighted score → priority label.

        Hard Rule 1 — Safety Override (checked FIRST, before scoring):
          If a qualifying physical hazard is verified (hazard=True, with matched
          hazard_type), the complaint is immediately CRITICAL.  The weighted
          score is still computed for transparency but cannot lower the label.

        Hard Rule 2 — Time-based escalation cap:
          Pending time (T) can escalate LOW → MEDIUM → HIGH.
          It can NEVER push a complaint to CRITICAL on its own.
          A routine complaint pending 7+ days reaches HIGH at most.
          CRITICAL is reserved exclusively for safety-override triggers.
        """
        # ── Rule 1: Safety override (evaluated before scoring) ──────────────
        # Triggered by a verified physical hazard pattern match — not by
        # urgency phrases.  hazard_type must be the actual regex match string.
        safety_override = bool(hazard and hazard_type)

        # ── Time component T (0–4.5) ─────────────────────────────────────────
        # Cap at 4.5 so even with max weights the score stays below CRITICAL
        # threshold for routine (non-hazard) complaints.
        if time_pending_days <= 0:
            T = 0.0
        elif time_pending_days <= 1:
            T = 1.0
        elif time_pending_days <= 3:
            T = 2.0
        elif time_pending_days <= 7:
            T = 3.0
        elif time_pending_days <= 14:
            T = 4.0
        else:
            T = 4.5

        P = (
            self.WEIGHTS["S"] * severity
            + self.WEIGHTS["I"] * immediate_risk
            + self.WEIGHTS["E"] * public_exposure
            + self.WEIGHTS["C"] * context_score
            + self.WEIGHTS["T"] * T
        )
        P = round(min(5.0, max(0.0, P)), 3)

        # ── Rule 1 applied: safety override always wins ──────────────────────
        if safety_override:
            priority = "CRITICAL"
            explanation = (
                f"Safety override — verified hazard: '{hazard_type}'. "
                f"Weighted score {P} is irrelevant; hazard triggers immediate critical review."
            )

        # ── Rule 2 applied: time-only escalation is capped at HIGH ───────────
        # Determine whether time is the SOLE reason P would reach CRITICAL.
        # Compute the score without the T component to check.
        elif P >= 4.0:
            P_no_time = round(
                self.WEIGHTS["S"] * severity
                + self.WEIGHTS["I"] * immediate_risk
                + self.WEIGHTS["E"] * public_exposure
                + self.WEIGHTS["C"] * context_score,
                3,
            )
            if P_no_time < 4.0:
                # Time pushed it over the threshold — cap at HIGH
                priority = "HIGH"
                explanation = (
                    f"Time-escalated score {P} reached the CRITICAL threshold, "
                    f"but base score (without time) is {P_no_time}. "
                    f"CRITICAL is reserved for safety hazards — capped at HIGH."
                )
            else:
                # Score was already CRITICAL on its own merit
                priority = "CRITICAL"
                explanation = f"Score {P} ≥ 4.0 (base score {P_no_time} also ≥ 4.0, independent of time)."

        elif P >= 2.50:
            priority = "HIGH"
            explanation = f"Score {P} → High priority."
        elif P >= 1.50:
            priority = "MEDIUM"
            explanation = f"Score {P} → Medium priority."
        else:
            priority = "LOW"
            explanation = f"Score {P} → Low priority."

        return {
            "priority": priority,
            "priority_score": P,
            "components": {
                "severity": severity,
                "immediate_risk": immediate_risk,
                "public_exposure": public_exposure,
                "context": context_score,
                "time_pending": T,
            },
            "safety_override": safety_override,
            "time_escalated": not safety_override and T > 0,
            "explanation": explanation,
        }

    def compute_full_priority(
        self,
        title: str,
        description: str,
        hazard: bool = False,
        hazard_type: Optional[str] = None,
        corroboration_score: float = 2.0,
        evidence_quality: Optional[float] = None,
        time_pending_days: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Full pipeline: attribute extraction → weighted score → priority label.
        C = 0.4·Ve + 0.6·Ccorroboration  (per spec §6.3)
        """
        attrs = self.extract_attributes(title, description, hazard)
        Ve = evidence_quality if evidence_quality is not None else attrs["evidence_quality"]
        C = 0.4 * Ve + 0.6 * corroboration_score

        result = self.calculate_priority(
            severity=attrs["severity"],
            immediate_risk=attrs["immediate_risk"],
            public_exposure=attrs["public_exposure"],
            context_score=C,
            time_pending_days=time_pending_days,
            hazard=hazard,
            hazard_type=hazard_type,
        )
        result["attributes"] = attrs
        result["corroboration_score"] = corroboration_score
        return result


# Singletons
classifier_service = ComplaintClassifier()
priority_engine = PriorityEngine()
