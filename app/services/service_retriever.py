
import json
from pathlib import Path
from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

class ServiceRetriever:
    """Retrieve relevant Cynbit services from the local knowledge base."""

    def __init__(self, knowledge_file: str | Path | None = None):
        if knowledge_file is None:
            knowledge_file = (
                Path(__file__).resolve().parents[1]
                / "knowledge"
                / "services.json"
            )

        self.knowledge_file = Path(knowledge_file)
        self.services = self._load_services()

        if not self.services:
            raise ValueError("The service knowledge base is empty.")

        self.documents = [
            self._build_document(service)
            for service in self.services
        ]

        self.vectorizer = TfidfVectorizer(
            lowercase=True,
            stop_words="english",
            ngram_range=(1, 2),
            sublinear_tf=True,
        )

        self.document_vectors = self.vectorizer.fit_transform(
            self.documents
        )

    def _load_services(self) -> list[dict[str, Any]]:
        if not self.knowledge_file.exists():
            raise FileNotFoundError(
                f"Knowledge base not found: {self.knowledge_file}"
            )

        with self.knowledge_file.open("r", encoding="utf-8") as file:
            services = json.load(file)

        if not isinstance(services, list):
            raise ValueError("Knowledge base must contain a JSON list.")

        return services

    @staticmethod
    def _build_document(service: dict[str, Any]) -> str:
        fields = [
            service.get("name", ""),
            service.get("category", ""),
            service.get("description", ""),
            " ".join(service.get("capabilities", [])),
            " ".join(service.get("ideal_for", [])),
            " ".join(service.get("keywords", [])),
        ]

        return " ".join(str(field) for field in fields if field)

    def search(
        self,
        query: str,
        top_k: int = 3,
    ) -> list[dict[str, Any]]:
        """Return the most relevant services for an enquiry."""

        if not query or not query.strip():
            return []

        if top_k < 1:
            raise ValueError("top_k must be at least 1.")

        query_vector = self.vectorizer.transform([query.strip()])

        similarities = cosine_similarity(
            query_vector,
            self.document_vectors,
        ).flatten()

        ranked_indices = similarities.argsort()[::-1][:top_k]

        results = []

        for index in ranked_indices:
            score = float(similarities[index])

            if score <= 0:
                continue

            service = self.services[index]

            results.append({
                "service_id": service["id"],
                "service_name": service["name"],
                "category": service["category"],
                "description": service["description"],
                "capabilities": service["capabilities"],
                "relevance_score": round(score, 4),
            })

        return results

# Reuse one initialized retriever instead of rebuilding it per request.
service_retriever = ServiceRetriever()