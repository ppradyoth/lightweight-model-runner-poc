# Private AI in 4 Python files: local RAG with Qwen, FAISS, and llama.cpp

Run a private, offline document assistant on one machine. This is a deliberately small local RAG proof of concept for teams evaluating on-premises LLM applications, self-hosted AI, edge AI, and air-gapped inference.

It indexes local Markdown, PDF, and text files, retrieves relevant passages with FAISS vector search, and answers with a quantized Qwen2.5 1.5B GGUF model through `llama.cpp`. Once the model files are downloaded, document ingestion and inference stay on the machine.

No OpenAI API. No hosted vector database. No cloud inference. No application server. Four Python files.

**Private documents in. Source-grounded answers out. No model-provider calls after setup.**

## The 60-second version

- **Private AI:** prompts, retrieved text, and generated answers stay local after model setup.
- **Offline RAG:** Qwen2.5 GGUF inference, MiniLM embeddings, and FAISS retrieval run on-device.
- **Enterprise evaluation starting point:** small enough to audit before adding your own identity, access, security, and deployment controls.
- **Real document Q&A:** ingest PDFs, Markdown, and text. Get an answer plus the source filenames.
- **No framework maze:** the entire retrieval and inference path fits in `ingest.py`, `rag.py`, and `cli.py`.

## Why this exists

Most local-LLM examples either stop at chat or arrive as a full platform. This repository isolates the smallest useful enterprise pattern:

```text
local documents
      |
      v
text extraction -> chunking -> local embeddings -> FAISS index
                                                   |
question -> local embedding -> top-k retrieval -----+
                                                   |
                                                   v
                                      local GGUF model -> answer + sources
```

Use it to answer a practical first question: can a useful private knowledge assistant run inside our environment without sending document content or prompts to a model provider?

This is for teams searching for a minimal local LLM example, offline RAG pipeline, self-hosted document chatbot, private enterprise search POC, or air-gapped generative AI starting point without adopting a full platform first.

## What it proves

- Local inference with a quantized GGUF model
- Local semantic search with `all-MiniLM-L6-v2` and FAISS
- Retrieval over `.md`, `.pdf`, and `.txt` files
- Answers prompted to use retrieved context and say when the answer is absent
- Source filenames returned with every answer
- Apple Silicon acceleration through Metal

This is a minimum POC, not a production RAG platform. It intentionally leaves authentication, authorization, encryption, audit logging, evaluation, observability, document-level access control, prompt-injection defenses, and deployment packaging to the system around it.

## Quick start

```bash
git clone https://github.com/ppradyoth/lightweight-model-runner-poc.git
cd lightweight-model-runner-poc

python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/pip install huggingface_hub

.venv/bin/hf download \
  Qwen/Qwen2.5-1.5B-Instruct-GGUF \
  qwen2.5-1.5b-instruct-q4_k_m.gguf \
  --local-dir models
```

Add your documents:

```bash
cp /path/to/your/files/* docs/
.venv/bin/python ingest.py
.venv/bin/python cli.py
```

Then ask a question:

```text
RAG ready. Ctrl+C to exit.

> What is our incident escalation path?

...

Sources: incident-response.md
```

The embedding model is also downloaded on first use. For an air-gapped deployment, download and approve both model artifacts in a connected staging environment, then transfer the GGUF and populated model cache through your normal artifact process.

## Repository map

| File | Responsibility |
|---|---|
| `ingest.py` | Extracts text, creates overlapping chunks, embeds them, and writes the FAISS index |
| `rag.py` | Loads the local models and index, retrieves context, and generates an answer |
| `cli.py` | Runs the interactive question-and-answer loop |
| `requirements.txt` | Lists the five runtime dependencies |

Generated artifacts stay simple too: `index.faiss` contains the vectors and `chunks.jsonl` contains the corresponding source text.

## Enterprise evaluation checklist

Before building a larger system around this POC, measure it with your own documents and hardware:

1. Answer quality: create questions with known answers and expected source files.
2. Grounding: verify that unsupported questions return "I don't know."
3. Retrieval: inspect whether the correct passage appears in the top four results.
4. Performance: record cold start, first-token latency, tokens per second, and peak memory.
5. Data boundary: monitor outbound traffic during ingestion and inference after model setup.
6. Access control: confirm retrieval never crosses the requesting user's document permissions.
7. Adversarial content: test instructions embedded inside documents. The system prompt alone is not a prompt-injection defense.

## Current boundaries

- The index has no per-user or per-document authorization layer.
- Retrieved text is untrusted model input.
- PDF extraction handles text PDFs, not scanned-image OCR.
- The first GGUF found in `models/` is loaded.
- The context window is fixed at 4,096 tokens and retrieval at four chunks.
- Dependency versions are not pinned for reproducible production builds.
- Model and dependency licenses must be reviewed for your deployment.

## macOS note

On this POC's Apple Silicon path, `llama_cpp` and its `Llama` instance must load before `faiss` and `sentence_transformers`. Reversing that order can trigger a native-library conflict. `rag.py` preserves the working import and initialization order.

`n_gpu_layers=-1` offloads all model layers to Metal. Other platforms may need a different `llama-cpp-python` build and GPU configuration.

## Good next steps

If this minimum path works on your corpus, the next useful additions are an evaluation set, metadata-aware retrieval, document-level authorization, signed model artifacts, dependency locking, an API boundary, and auditable request logs.

Keep the core small until the measurements justify more.
