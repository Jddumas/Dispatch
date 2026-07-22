"""
Week 1, Day 3-4: Streaming LLM responses from a local Ollama model.
"""

import ollama


def main() -> None:
    stream = ollama.chat(
        model="llama3.1",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a knowledgeable AI assistant. "
                    "Answer questions accurately and concisely."
                ),
            },
            {
                "role": "user",
                "content": (
                    "In the context of AI and large language models, "
                    "what does RAG stand for? Give a one-sentence definition."
                ),
            },
        ],
        options={
            "temperature": 0.3,
            "num_predict": 300,
        },
        stream=True,
    )

    print("Assistant: ", end="", flush=True)
    for chunk in stream:
        content = chunk["message"]["content"]
        print(content, end="", flush=True)
    print()


if __name__ == "__main__":
    main()
