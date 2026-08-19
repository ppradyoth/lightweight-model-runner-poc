import json
from pathlib import Path

# llama_cpp must import (and its Llama instance load) before faiss/torch,
# or their dylibs conflict and segfault on macOS.
from llama_cpp import Llama
import faiss
from sentence_transformers import SentenceTransformer

BASE_DIR = Path(__file__).parent
INDEX_PATH = BASE_DIR / "index.faiss"
CHUNKS_PATH = BASE_DIR / "chunks.jsonl"
MODELS_DIR = BASE_DIR / "models"
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
TOP_K = 4

SYSTEM_PROMPT = (
    "Answer the question using only the provided context. "
    "If the context doesn't contain the answer, say you don't know."
)


def find_gguf() -> Path:
    ggufs = list(MODELS_DIR.glob("*.gguf"))
    if not ggufs:
        raise SystemExit(f"No .gguf model found in {MODELS_DIR}")
    return ggufs[0]


class RAG:
    def __init__(self):
        # llama-cpp-python's Metal backend must init before torch (via
        # sentence-transformers) loads, or the two segfault on macOS.
        self.llm = Llama(
            model_path=str(find_gguf()), n_ctx=4096, n_gpu_layers=-1, verbose=False
        )
        self.embed_model = SentenceTransformer(EMBED_MODEL)
        self.index = faiss.read_index(str(INDEX_PATH))
        self.chunks = [json.loads(line) for line in CHUNKS_PATH.open()]
        self._warmup()

    def _warmup(self):
        # First inference call pays extra one-time setup cost (KV cache
        # alloc, compute graph build) beyond just loading weights - eat that
        # cost here so it doesn't land on the user's first real question.
        self.embed_model.encode(["warmup"], normalize_embeddings=True)
        self.llm.create_chat_completion(
            messages=[{"role": "user", "content": "hi"}], max_tokens=1
        )

    def retrieve(self, query: str, k: int = TOP_K):
        q_emb = self.embed_model.encode([query], normalize_embeddings=True)
        _, indices = self.index.search(q_emb, k)
        return [self.chunks[i] for i in indices[0] if i != -1]

    def answer(self, query: str):
        retrieved = self.retrieve(query)
        context = "\n\n".join(f"[{c['source']}]\n{c['text']}" for c in retrieved)
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"},
        ]
        result = self.llm.create_chat_completion(
            messages=messages, temperature=0.2, repeat_penalty=1.15, max_tokens=512
        )
        return result["choices"][0]["message"]["content"], retrieved
