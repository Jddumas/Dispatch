"""
Week 1, Day 3-4: LLM API Basics
A basic script that sends a prompt to a local Ollama model and prints the response.
"""

import ollama


def main() -> None:
    response = ollama.chat(
        model="llama3.1",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a knowledgeable AI assistant. "
                    "Answer questions accurately and concisely."
                ),
            },
            {"role": "user", "content": "In the context of AI and large language models, what does RAG stand for? Give a one-sentence definition."},
        ],
        options={
            "temperature": 0.3,
            "num_predict": 300,
        },
    )
    print(response["message"]["content"])


if __name__ == "__main__":
    main()
