import os
import json
import numpy as np
from dotenv import load_dotenv
from google import genai

from agents.config import RETRIEVAL_EMBEDDING_MODEL

load_dotenv()

SEED_DATA_PATH = "data/seed_complaints.json"
INDEX_CACHE_PATH = "data/embeddings_cache.npz"


class RetrievalAgent:
    def __init__(self, similarity_threshold=0.5):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment.")
        self.client = genai.Client(api_key=api_key)
        self.similarity_threshold = similarity_threshold

        self.complaints = self._load_seed_data()
        self.embeddings = self._load_or_build_index()

    def _load_seed_data(self):
        with open(SEED_DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    def _embed_text(self, text: str) -> np.ndarray:
        response = self.client.models.embed_content(
            model=RETRIEVAL_EMBEDDING_MODEL,
            contents=text,
        )
        return np.array(response.embeddings[0].values)

    def _load_or_build_index(self) -> np.ndarray:
        if os.path.exists(INDEX_CACHE_PATH):
            cached = np.load(INDEX_CACHE_PATH)
            if cached["count"] == len(self.complaints):
                print(f"  [retrieval] Loaded cached embeddings for {len(self.complaints)} complaints.")
                return cached["embeddings"]

        print(f"  [retrieval] Building embeddings for {len(self.complaints)} complaints...")
        vectors = []
        for item in self.complaints:
            vec = self._embed_text(item["complaint_text"])
            vectors.append(vec)
        embeddings = np.array(vectors)

        np.savez(INDEX_CACHE_PATH, embeddings=embeddings, count=len(self.complaints))
        return embeddings

    @staticmethod
    def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

    def retrieve(self, query_text: str, top_k=3) -> list:
        query_vec = self._embed_text(query_text)

        scored = []
        for item, vec in zip(self.complaints, self.embeddings):
            score = self._cosine_similarity(query_vec, vec)
            scored.append((score, item))

        scored.sort(key=lambda x: x[0], reverse=True)
        top_matches = scored[:top_k]

        results = []
        for score, item in top_matches:
            if score >= self.similarity_threshold:
                results.append({
                    "id": item["id"],
                    "complaint_text": item["complaint_text"],
                    "category": item["category"],
                    "resolution": item["resolution"],
                    "similarity_score": round(score, 4),
                })

        if not results:
            return {"precedents": [], "fallback": "no_precedent_found"}

        return {"precedents": results, "fallback": None}


if __name__ == "__main__":
    agent = RetrievalAgent()

    test_query = "I keep getting double charged on my account every month and nobody is helping me."
    result = agent.retrieve(test_query)
    print(json.dumps(result, indent=2))