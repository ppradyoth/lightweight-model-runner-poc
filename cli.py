from rag import RAG


def main():
    rag = RAG()
    print("RAG ready. Ctrl+C to exit.\n")
    while True:
        try:
            query = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not query:
            continue
        answer, sources = rag.answer(query)
        print(f"\n{answer}\n")
        print("Sources:", ", ".join(sorted({s["source"] for s in sources})))
        print()


if __name__ == "__main__":
    main()
