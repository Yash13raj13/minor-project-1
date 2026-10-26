import logging
from typing import Dict, List, Optional, Tuple
import numpy as np

logger = logging.getLogger(__name__)


class DuplicateFinderService:
    """
    Semantic Duplicate Grievance Detection using Sentence-Transformers & FAISS.
    Calculates high-dimensional vector embeddings and finds nearest cosine neighbors.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2", dimension: int = 384):
        self.model_name = model_name
        self.dimension = dimension
        self.encoder = None
        self.index = None
        self.id_map: List[int] = []  # FAISS index pos -> complaint_id
        self._initialized = False

    def _lazy_init(self):
        if self._initialized:
            return
        try:
            from sentence_transformers import SentenceTransformer
            import faiss

            logger.info(f"Loading Sentence-Transformer model '{self.model_name}'...")
            self.encoder = SentenceTransformer(self.model_name)
            # Inner product on normalized vectors = Cosine Similarity
            self.index = faiss.IndexFlatIP(self.dimension)
            logger.info("FAISS vector index initialized successfully.")
        except Exception as e:
            logger.warning(
                f"SentenceTransformers or FAISS not available ({e}). Using cosine fallback mode."
            )
            self.encoder = None
            self.index = None
            # In-memory document texts cache for fallback
            self.fallback_corpus: Dict[int, str] = {}
        finally:
            self._initialized = True

    def _encode(self, text: str) -> np.ndarray:
        if self.encoder:
            vec = self.encoder.encode([text], convert_to_numpy=True)
            # L2 normalize for cosine similarity via inner product
            norm = np.linalg.norm(vec, axis=1, keepdims=True)
            vec = vec / np.maximum(norm, 1e-12)
            return vec.astype("float32")
        return None

    def add_complaint(self, complaint_id: int, title: str, description: str):
        """
        Embeds a new complaint and appends it to the FAISS vector index.
        """
        self._lazy_init()
        text = f"{title}. {description}".strip()

        if self.index is not None and self.encoder is not None:
            embedding = self._encode(text)
            self.index.add(embedding)
            self.id_map.append(complaint_id)
            logger.info(f"Added complaint {complaint_id} to FAISS index. Total: {self.index.ntotal}")
        else:
            if not hasattr(self, "fallback_corpus"):
                self.fallback_corpus = {}
            self.fallback_corpus[complaint_id] = text.lower()

    def find_duplicates(
        self,
        title: str,
        description: str,
        top_k: int = 5,
        similarity_threshold: float = 0.80,
    ) -> List[Dict]:
        """
        Searches the FAISS index for semantically similar complaints exceeding threshold.
        """
        self._lazy_init()
        query_text = f"{title}. {description}".strip()
        results = []

        if self.index is not None and self.encoder is not None and self.index.ntotal > 0:
            query_vec = self._encode(query_text)
            k = min(top_k, self.index.ntotal)
            similarities, indices = self.index.search(query_vec, k)

            for sim, idx in zip(similarities[0], indices[0]):
                if idx < len(self.id_map) and idx != -1:
                    score = float(sim)
                    if score >= similarity_threshold:
                        results.append(
                            {
                                "complaint_id": self.id_map[idx],
                                "similarity_score": round(score, 4),
                            }
                        )
        elif hasattr(self, "fallback_corpus") and self.fallback_corpus:
            # Fallback simple Jaccard / token-overlap similarity
            query_words = set(query_text.lower().split())
            for c_id, text in self.fallback_corpus.items():
                target_words = set(text.split())
                intersection = len(query_words & target_words)
                union = len(query_words | target_words)
                score = intersection / union if union > 0 else 0.0
                if score >= 0.35:  # Scaled threshold for word overlap
                    results.append(
                        {
                            "complaint_id": c_id,
                            "similarity_score": round(min(0.99, score * 1.8), 4),
                        }
                    )
            results.sort(key=lambda x: x["similarity_score"], reverse=True)
            results = results[:top_k]

        return results

    def rebuild_index(self, complaints: List[Tuple[int, str, str]]):
        """
        Clears and re-populates the vector index with a fresh list of complaints:
        complaints: List of (id, title, description)
        """
        self._lazy_init()
        if self.index is not None:
            import faiss
            self.index = faiss.IndexFlatIP(self.dimension)
            self.id_map = []
        if hasattr(self, "fallback_corpus"):
            self.fallback_corpus.clear()

        for c_id, title, desc in complaints:
            self.add_complaint(c_id, title, desc)
        logger.info(f"FAISS index rebuilt with {len(complaints)} complaints.")


duplicate_service = DuplicateFinderService()

