import json
from pathlib import Path

import faiss
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer

DOCS_DIR = Path(__file__).parent / "docs"
INDEX_PATH = Path(__file__).parent / "index.faiss"
CHUNKS_PATH = Path(__file__).parent / "chunks.jsonl"
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def load_text(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    return path.read_text(errors="ignore")


def main():
    splitter = RecursiveCharacterTextSplitter(chunk_size=1600, chunk_overlap=200)
    model = SentenceTransformer(EMBED_MODEL)

    chunks = []
    for path in sorted(DOCS_DIR.glob("*")):
        if path.suffix.lower() not in (".md", ".pdf", ".txt"):
            continue
        text = load_text(path)
        for chunk in splitter.split_text(text):
            chunks.append({"source": path.name, "text": chunk})

    if not chunks:
        raise SystemExit(f"No chunks found in {DOCS_DIR}")

    embeddings = model.encode([c["text"] for c in chunks], normalize_embeddings=True)
    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)

    faiss.write_index(index, str(INDEX_PATH))
    with open(CHUNKS_PATH, "w") as f:
        for c in chunks:
            f.write(json.dumps(c) + "\n")

    print(f"Indexed {len(chunks)} chunks from {DOCS_DIR} -> {INDEX_PATH}")


if __name__ == "__main__":
    main()
