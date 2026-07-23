"""
Week 3: RAG Pipeline — combine ChromaDB retrieval with a local Ollama LLM.
"""

import sys
from pathlib import Path

# Add project root to the path so we can import app.tools.retriever.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.tools import retriever


def main() -> None:
    print("Indexing knowledge base documents...")
    count = retriever.index_documents()
    print(f"Indexed {count} chunks.\n")

    questions = [
        "How long do I have to return an item?",
        "What is the warranty coverage for products?",
        "How do I reset my password?",
        "How long does standard shipping take?",
        "What are the troubleshooting steps for a wireless device that will not connect?",
        "What is the battery life of the noise-canceling headphones?",
    ]

    for question in questions:
        result = retriever.answer(question, k=3)
        print(f"Q: {result['query']}")
        print(f"A: {result['answer']}")
        print("Sources:")
        for match in result["matches"]:
            print(f"  - {match['metadata']['title']}")
        print()


if __name__ == "__main__":
    main()
