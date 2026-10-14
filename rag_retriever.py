
# rag_retriever.py
# TF-IDF retrieval for AgentiQ-Genomics

from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

import query_engine as qe


BASE_DIR = Path(__file__).resolve().parent
KNOWLEDGE_BASE_DIR = BASE_DIR / "knowledge_base"


class RAGRetriever:
    def __init__(self):
        self.documents = []
        self.sources = []

        for path in sorted(KNOWLEDGE_BASE_DIR.glob("*.txt")):
            text = path.read_text(encoding="utf-8").strip()

            if text:
                self.documents.append(text)
                self.sources.append(path.name)

        # Add exact values from the loaded dataset.
        schema = qe.search_schema()

        self.documents.append(
            "Valid chromosomes: "
            + ", ".join(schema["chromosomes"])
        )
        self.sources.append("query_engine:chromosomes")

        self.documents.append(
            "Valid mutation classifications: "
            + ", ".join(schema["variant_classifications"])
        )
        self.sources.append("query_engine:variants")

        self.documents.append(
            "Genome assembly: " + str(schema["assembly"])
        )
        self.sources.append("query_engine:assembly")

        if not self.documents:
            raise ValueError("RAG knowledge base is empty.")

        self.vectorizer = TfidfVectorizer()
        self.matrix = self.vectorizer.fit_transform(
            self.documents
        )

    def retrieve(self, question, k=4):
        query_vector = self.vectorizer.transform([question])

        scores = cosine_similarity(
            query_vector, self.matrix
        )[0]

        ranked = scores.argsort()[::-1][:k]

        return [
            {
                "source": self.sources[i],
                "text": self.documents[i],
                "score": float(scores[i]),
            }
            for i in ranked
            if scores[i] > 0
        ]
