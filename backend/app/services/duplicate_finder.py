"""
CivicLens AI/ML Pipeline — Stage 4 & 5: Semantic Duplicate Detection + Corroboration

Model: Indic BGE-M3 (karmx/Llama-Karmx-Indic-Embedding-bge-m3)
Fallback: all-MiniLM-L6-v2 (multilingual capable, lighter)
Search: FAISS IndexFlatIP (cosine via L2-normalised vectors)
Corroboration: C_corroboration = min(5, 2·log2(1 + N_unique_users))
"""
import logging
import math
from typing import Dict, List, Optional, Tuple
import numpy as np

logger = logging.getLogger(__name__)

THRESHOLD_UNLIKELY  = 0.65
THRESHOLD_POSSIBLE  = 0.80
THRESHOLD_STRONG    = 0.90
GEO_WINDOW_DEGREES  = 0.015   # ~1.5 km


class DuplicateFinderService:
    """
    Semantic duplicate detection using Indic BGE-M3 embeddings + FAISS.
    Fine-tuning: call load_finetuned_model() after Sentence Transformers training.
    """

    PREFERRED_MODELS = [
        "karmx/Llama-Karmx-Indic-Embedding-bge-m3",
        "BAAI/bge-m3",
        "all-MiniLM-L6-v2",
    ]

    def __init__(self):
        self.encoder = None
        self.index = None
        self.dimension: int = 384
        self.id_map: List[int] = []
        self.metadata: Dict[int, Dict] = {}
        self._initialized = False
        self._model_name: str = "none"

    def _lazy_init(self):
        if self._initialized:
            return
        self._initialized = True
        try:
            from sentence_transformers import SentenceTransformer
            import faiss

            encoder = None
            for model_name in self.PREFERRED_MODELS:
                try:
                    encoder = SentenceTransformer(model_name)
                    test_vec = encoder.encode(["test"], convert_to_numpy=True)
                    self.dimension = test_vec.shape[1]
                    self._model_name = model_name
                    logger.info(f"Embedding model '{model_name}' loaded (dim={self.dimension}).")
                    break
                except Exception as e:
                    logger.warning(f"Could not load '{model_name}': {e}")

            self.encoder = encoder
            self.index = faiss.IndexFlatIP(self.dimension)
        except Exception as e:
            logger.warning(f"SentenceTransformers/FAISS unavailable: {e}. Fallback active.")
            self.encoder = None
            self.index = None
            self._fallback_corpus: Dict[int, str] = {}

    def load_finetuned_model(self, model_path: str):
        from sentence_transformers import SentenceTransformer
        import faiss
        self.encoder = SentenceTransformer(model_path)
        test_vec = self.encoder.encode(["test"], convert_to_numpy=True)
        new_dim = test_vec.shape[1]
        if new_dim != self.dimension:
            self.dimension = new_dim
            self.index = faiss.IndexFlatIP(new_dim)
            self.id_map = []
            self.metadata = {}
            logger.warning("Dimension changed — FAISS index reset. Call rebuild_index().")
        self._model_name = model_path
        logger.info(f"Fine-tuned embedding model loaded from: {model_path}")

    def _encode(self, text: str) -> Optional[np.ndarray]:
        if self.encoder is None:
            return None
        vec = self.encoder.encode([text], convert_to_numpy=True, normalize_embeddings=True)
        return vec.astype("float32")

    def add_complaint(
        self,
        complaint_id: int,
        title: str,
        description: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        category: Optional[str] = None,
        created_at: Optional[str] = None,
    ):
        self._lazy_init()
        text = f"{title}. {description}".strip()

        if self.index is not None and self.encoder is not None:
            vec = self._encode(text)
            if vec is not None:
                self.index.add(vec)
                self.id_map.append(complaint_id)
        else:
            if not hasattr(self, "_fallback_corpus"):
                self._fallback_corpus = {}
            self._fallback_corpus[complaint_id] = text.lower()

        self.metadata[complaint_id] = {
            "latitude": latitude,
            "longitude": longitude,
            "category": category,
            "created_at": created_at,
        }

    def find_duplicates(
        self,
        title: str,
        description: str,
        top_k: int = 5,
        similarity_threshold: float = THRESHOLD_POSSIBLE,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        category: Optional[str] = None,
    ) -> List[Dict]:
        self._lazy_init()
        query_text = f"{title}. {description}".strip()
        candidates = []

        if self.index is not None and self.encoder is not None and self.index.ntotal > 0:
            query_vec = self._encode(query_text)
            if query_vec is not None:
                k = min(top_k + 2, self.index.ntotal)
                sims, indices = self.index.search(query_vec, k)
                for sim, idx in zip(sims[0], indices[0]):
                    if idx < 0 or idx >= len(self.id_map):
                        continue
                    score = float(sim)
                    if score < similarity_threshold:
                        continue
                    cid = self.id_map[idx]
                    meta = self.metadata.get(cid, {})
                    geo_match = self._check_geo(latitude, longitude, meta.get("latitude"), meta.get("longitude"))
                    same_category = (category is None or meta.get("category") == category)
                    adjusted = min(1.0, score + (0.05 if geo_match else 0.0))
                    candidates.append({
                        "complaint_id": cid,
                        "similarity_score": round(adjusted, 4),
                        "text_similarity": round(score, 4),
                        "geo_match": geo_match,
                        "same_category": same_category,
                    })

        elif hasattr(self, "_fallback_corpus") and self._fallback_corpus:
            query_words = set(query_text.lower().split())
            for cid, stored_text in self._fallback_corpus.items():
                target_words = set(stored_text.split())
                inter = len(query_words & target_words)
                union = len(query_words | target_words)
                jaccard = inter / union if union > 0 else 0.0
                sim = min(0.98, jaccard * 1.9)
                if sim >= similarity_threshold:
                    meta = self.metadata.get(cid, {})
                    geo_match = self._check_geo(latitude, longitude, meta.get("latitude"), meta.get("longitude"))
                    candidates.append({
                        "complaint_id": cid,
                        "similarity_score": round(sim, 4),
                        "text_similarity": round(sim, 4),
                        "geo_match": geo_match,
                        "same_category": True,
                    })
            candidates.sort(key=lambda x: x["similarity_score"], reverse=True)

        return candidates[:top_k]

    def _check_geo(self, lat1, lon1, lat2, lon2) -> bool:
        if any(v is None for v in [lat1, lon1, lat2, lon2]):
            return False
        return abs(lat1 - lat2) <= GEO_WINDOW_DEGREES and abs(lon1 - lon2) <= GEO_WINDOW_DEGREES

    def rebuild_index(self, complaints: List[Tuple]):
        self._lazy_init()
        if self.index is not None:
            import faiss
            self.index = faiss.IndexFlatIP(self.dimension)
        self.id_map = []
        self.metadata = {}
        if hasattr(self, "_fallback_corpus"):
            self._fallback_corpus = {}

        for item in complaints:
            if len(item) >= 7:
                cid, title, desc, lat, lon, cat, created = item[0], item[1], item[2], item[3], item[4], item[5], item[6]
            elif len(item) >= 3:
                cid, title, desc = item[0], item[1], item[2]
                lat = lon = cat = created = None
            else:
                continue
            self.add_complaint(cid, title, desc, lat, lon, cat, created)
        logger.info(f"FAISS index rebuilt — {len(complaints)} complaints indexed.")

    @property
    def index_size(self) -> int:
        return len(self.id_map)

    @property
    def model_name(self) -> str:
        return self._model_name

    def load_finetuned_model(self, model_path: str):
        from sentence_transformers import SentenceTransformer
        self._model = SentenceTransformer(model_path)
        self.dimension = self._model.get_sentence_embedding_dimension()
        self._model_name = f"Custom Fine-tuned ({model_path})"
        self._initialized = True
        logger.info(f"Custom embedding model loaded from: {model_path} (dimension: {self.dimension})")


# ---------------------------------------------------------------------------
# Corroboration Scoring Engine  (§6.2)
# ---------------------------------------------------------------------------

class CorroborationEngine:
    """
    C_corroboration = min(5, 2·log2(1 + N))
    C = 0.4·Ve + 0.6·C_corroboration
    """

    @staticmethod
    def corroboration_score(unique_users: int) -> float:
        if unique_users <= 0:
            return 0.0
        return round(min(5.0, 2.0 * math.log2(1 + unique_users)), 3)

    @staticmethod
    def context_score(evidence_quality: float, unique_users: int) -> float:
        C_corr = CorroborationEngine.corroboration_score(unique_users)
        return round(0.4 * evidence_quality + 0.6 * C_corr, 3)

    @staticmethod
    def ip_similarity_flag(ip_hash_a: Optional[str], ip_hash_b: Optional[str]) -> bool:
        """WEAK supplementary signal only — never auto-rejects."""
        if ip_hash_a is None or ip_hash_b is None:
            return False
        return ip_hash_a == ip_hash_b


# Singletons
duplicate_service = DuplicateFinderService()
corroboration_engine = CorroborationEngine()
