# lightweight-model-runner-poc

RAG over local documents using a small, local LLM (Qwen2.5-1.5B-Instruct GGUF)
and a lightweight embedding model (all-MiniLM-L6-v2), fully on-device via
`llama-cpp-python` and FAISS.

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Download a GGUF quant of Qwen2.5-1.5B-Instruct into `models/`:

```bash
.venv/bin/pip install huggingface_hub
.venv/bin/hf download Qwen/Qwen2.5-1.5B-Instruct-GGUF qwen2.5-1.5b-instruct-q4_k_m.gguf --local-dir models
```

Drop your own `.md` / `.pdf` / `.txt` files into `docs/`, then:

```bash
.venv/bin/python ingest.py   # builds index.faiss + chunks.jsonl
.venv/bin/python cli.py      # interactive Q&A
```

## Notes

- On macOS, `llama_cpp` must be imported (and its `Llama` instance created)
  before `faiss`/`sentence_transformers` — importing in the wrong order
  segfaults due to a dylib conflict between llama.cpp's Metal backend and
  torch. See the comment in `rag.py`.
- `n_gpu_layers=-1` offloads all layers to Metal on Apple Silicon.
- The model only answers from retrieved context and says "I don't know"
  otherwise — it will refuse questions unrelated to your `docs/`.
