from rag_retriever import RAGRetriever

retriever = RAGRetriever()

results = retriever.retrieve(
    "Show missense mutations on chromosome 7"
)

for result in results:
    print("SOURCE:", result["source"])
    print("SCORE:", round(result["score"], 4))
    print("TEXT:", result["text"])
    print("-" * 50)