"""
CivicLens AI/ML Pipeline — Stage 1: Multilingual Data Preprocessing
Handles English, Hindi and Hinglish complaint normalisation.
Uses: langdetect (fastText-compatible fallback), unicode normalisation, regex cleaning.
"""
import re
import logging
import unicodedata
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Hinglish / Romanised-Hindi civic keyword dictionaries
# ---------------------------------------------------------------------------
HINGLISH_CIVIC_LEXICON = {
    # Roads
    "gaddha": "pothole", "gadha": "pothole", "sadak": "road", "rasta": "road",
    "pul": "bridge", "footpath": "footpath", "pothol": "pothole",
    # Water
    "paani": "water", "pani": "water", "nali": "drain", "naali": "drain",
    "pipeline": "pipeline", "leakage": "leakage",
    # Sanitation
    "kachra": "garbage", "kuda": "garbage", "safai": "cleaning",
    # Electricity
    "bijli": "electricity", "light": "light", "taar": "wire",
    # Health
    "machchar": "mosquito", "gandag": "filth", "bimari": "disease",
    # Urgency
    "bahut": "very", "bada": "big", "bhari": "heavy", "urgent": "urgent",
    "jaldi": "immediately", "khatarnak": "dangerous", "tehran": "emergency",
    "nahi": "not", "nhi": "not", "nahi hai": "not available",
    "ho sakta": "can happen", "ho raha": "is happening",
}

# Words that MUST NOT be removed — negations, intensity markers, location-sensitive
PRESERVE_WORDS = {
    "not", "nahi", "nhi", "nahi", "never", "no", "without",
    "very", "extremely", "highly", "immediately", "urgent", "danger", "dangerous",
    "bahut", "bada", "jaldi", "khatarnak",
}


class TextPreprocessor:
    """
    Multilingual preprocessor for civic complaints.
    Maintains two versions: original (for transformer/officer review)
    and normalised (for rule-based matching and keyword scoring).
    """

    def __init__(self):
        self._lang_detector = None
        self._stanza_en = None
        self._stanza_hi = None
        self._stanza_initialized = {}

    # ------------------------------------------------------------------
    # Language Detection
    # ------------------------------------------------------------------
    def detect_language(self, text: str) -> str:
        """
        Returns one of: 'en', 'hi', 'hinglish', 'other'.
        Uses langdetect with Hinglish heuristic override.
        """
        # Hinglish heuristic: has Latin script but contains Hinglish civic words
        latin_text = text.lower().strip()
        hinglish_hits = sum(1 for word in HINGLISH_CIVIC_LEXICON if word in latin_text.split())
        has_devanagari = bool(re.search(r'[\u0900-\u097F]', text))

        if has_devanagari:
            # Check if mixed (Devanagari + Latin = Hinglish/mixed)
            has_latin_words = bool(re.search(r'[a-zA-Z]{3,}', text))
            return "mixed" if has_latin_words else "hi"

        if hinglish_hits >= 1:
            return "hinglish"

        try:
            if self._lang_detector is None:
                from langdetect import detect, DetectorFactory
                DetectorFactory.seed = 42
                self._lang_detector = detect
            lang = self._lang_detector(text)
            if lang in ("hi", "ur"):
                return "hi"
            if lang == "en":
                return "en"
            return "other"
        except Exception:
            # Fallback: check ASCII ratio
            ascii_ratio = sum(1 for c in text if ord(c) < 128) / max(1, len(text))
            return "en" if ascii_ratio > 0.85 else "other"

    # ------------------------------------------------------------------
    # Unicode Normalisation
    # ------------------------------------------------------------------
    def unicode_normalise(self, text: str) -> str:
        """NFC normalisation for consistent Indic script representation."""
        try:
            return unicodedata.normalize("NFC", text)
        except Exception:
            return text

    # ------------------------------------------------------------------
    # Noise Cleaning
    # ------------------------------------------------------------------
    def clean_noise(self, text: str) -> str:
        """
        Remove HTML tags, excessive punctuation, repeated characters.
        DOES NOT remove negations, numbers, location names, intensity words.
        """
        # Strip HTML
        text = re.sub(r'<[^>]+>', ' ', text)
        # Normalise whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        # Remove special chars except . , ! ? - / & (preserve addresses)
        text = re.sub(r'[^\w\s.,!?/\-&\'\"()]', ' ', text, flags=re.UNICODE)
        # Collapse repeated punctuation
        text = re.sub(r'([!?.]){2,}', r'\1', text)
        # Collapse repeated characters (e.g., "hugeeeee" → "huge")
        text = re.sub(r'(.)\1{3,}', r'\1\1', text)
        return text.strip()

    # ------------------------------------------------------------------
    # Hinglish Normalisation (preserve Roman Hindi)
    # ------------------------------------------------------------------
    def normalise_hinglish(self, text: str) -> str:
        """
        Map known Hinglish civic terms to English equivalents for keyword matching.
        Original text is preserved separately for the transformer.
        """
        words = text.lower().split()
        result = []
        for word in words:
            clean_word = re.sub(r'[^\w]', '', word)
            mapped = HINGLISH_CIVIC_LEXICON.get(clean_word, word)
            result.append(mapped)
        return ' '.join(result)

    # ------------------------------------------------------------------
    # English Pipeline (Stanza)
    # ------------------------------------------------------------------
    def _get_stanza_en(self):
        if self._stanza_en is None and "en" not in self._stanza_initialized:
            self._stanza_initialized["en"] = True
            try:
                import stanza
                self._stanza_en = stanza.Pipeline(
                    lang="en",
                    processors="tokenize,pos,lemma",
                    verbose=False,
                    use_gpu=False,
                    download_method=None,
                )
            except Exception as e:
                logger.info(f"Stanza EN offline/not cached: {e}. Using standard regex tokenization fallback.")
                self._stanza_en = None
        return self._stanza_en

    def english_pipeline(self, text: str) -> str:
        """
        Tokenise and lemmatise English complaint text.
        IMPORTANT: Original text goes to transformer; this output is for
        rule-based matching only.
        """
        nlp = self._get_stanza_en()
        if nlp is None:
            return text.lower()
        try:
            doc = nlp(text)
            tokens = []
            for sentence in doc.sentences:
                for word in sentence.words:
                    # Preserve words in the must-keep list
                    if word.text.lower() in PRESERVE_WORDS:
                        tokens.append(word.text.lower())
                    else:
                        tokens.append(word.lemma.lower() if word.lemma else word.text.lower())
            return ' '.join(tokens)
        except Exception as e:
            logger.warning(f"Stanza EN pipeline failed: {e}")
            return text.lower()

    # ------------------------------------------------------------------
    # Hindi Pipeline
    # ------------------------------------------------------------------
    def hindi_pipeline(self, text: str) -> str:
        """
        Basic Hindi preprocessing: normalise Devanagari, remove stop-words carefully.
        Does not lemmatise — Hindi morphology is complex and not needed for BERT.
        """
        try:
            from indicnlp.normalize.indic_normalize import IndicNormalizerFactory
            normalizer = IndicNormalizerFactory().get_normalizer("hi")
            text = normalizer.normalize(text)
        except Exception:
            pass
        return text.lower().strip()

    # ------------------------------------------------------------------
    # Main Preprocessing Entry Point
    # ------------------------------------------------------------------
    def preprocess(self, text: str) -> Dict[str, str]:
        """
        Returns a dict with:
          - original_text: preserved as-is for transformer input and officer review
          - normalised_text: for rule-based keyword matching
          - language: detected language code
          - processed_text: lemmatised/mapped form for supplementary matching
        """
        original_text = text.strip()
        language = self.detect_language(original_text)
        normalised_text = self.unicode_normalise(original_text)
        normalised_text = self.clean_noise(normalised_text)

        if language == "en":
            processed_text = self.english_pipeline(normalised_text)
        elif language == "hi":
            processed_text = self.hindi_pipeline(normalised_text)
        elif language in ("hinglish", "mixed"):
            # For Hinglish, map civic terms but preserve Roman form
            processed_text = self.normalise_hinglish(normalised_text.lower())
        else:
            processed_text = normalised_text.lower()

        return {
            "original_text": original_text,
            "normalised_text": normalised_text,
            "processed_text": processed_text,
            "language": language,
        }


# Singleton
preprocessor = TextPreprocessor()

