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

## Developer guide: fold this into a real app

Do not ship this Python CLI inside every client. Keep the pipeline and replace the runtime at the platform boundary:

```text
pick local files
      |
extract text -> chunk -> embed -> store vectors locally
                                      |
user question -> embed -> retrieve ---+
                                      |
                                      v
                         build grounded prompt
                                      |
                                      v
                          on-device generation
                                      |
                                      v
                            answer + citations
```

The portable contract is small:

```json
{
  "id": "handbook.md#chunk-17",
  "source": "handbook.md",
  "text": "...",
  "embedding": [0.012, -0.031]
}
```

Keep chunk IDs, source metadata, prompt structure, retrieval tests, and model-version metadata consistent across platforms. Rebuild embeddings when you change the embedding model. Vectors created by different embedding models are not interchangeable.

### Pick the deployment shape first

| App | Where the LLM runs | Best fit | Main constraint |
|---|---|---|---|
| Internet app with server inference | Your private server | Broad browser support and centralized model updates | Prompts and retrieved text leave the device |
| Internet app with browser inference | WebGPU or WebAssembly inside the tab | Private document workflows with no inference bill | Model download, browser compatibility, memory, and storage quotas |
| iOS app | `llama.cpp` through an XCFramework with Metal | Controlled native experience and strong Apple Silicon performance | App size, memory pressure, thermal limits, and model delivery |
| Android app | `llama.cpp` through its Kotlin/native binding | Native offline inference across Android and ChromeOS hardware | Device fragmentation, ABI packaging, memory, and performance variance |

### Browser apps: keep the website online and inference local

The web server still delivers your HTML, JavaScript, authentication, and model manifest. The browser downloads the model once, stores it locally, and performs retrieval and generation on the user's hardware.

For this repository's GGUF model path, use [wllama](https://github.com/ngxson/wllama), a browser binding for `llama.cpp` with WebAssembly and WebGPU support. If you can distribute an MLC-compiled model instead of GGUF, [WebLLM](https://webllm.io/docs/guides/local-inference/) provides a browser-native WebGPU runtime. Do not treat the formats as drop-in replacements.

Use [Transformers.js](https://huggingface.co/docs/transformers.js/en/index) for browser-side embeddings. Its documented feature-extraction pipeline can run on WebGPU. For a minimum POC, keep normalized vectors in IndexedDB and calculate cosine similarity in a Web Worker. Move to a dedicated browser vector index only after the corpus makes linear search too slow.

Browser integration flow:

1. Check `navigator.gpu` and available storage before offering local mode.
2. Ask before downloading a model that may be hundreds of megabytes or larger.
3. Cache model assets and embeddings under the application's origin.
4. Run model loading, embedding, retrieval, and generation outside the UI thread.
5. Stream tokens back to the page and render the source IDs with the answer.
6. Provide a server-inference fallback only when the user or enterprise policy allows data to leave the device.

WebGPU requires HTTPS and is not available in every browser. Browser-managed data can also be evicted. Use the [Storage API](https://developer.mozilla.org/en-US/docs/Web/API/Storage_API) to estimate space and request persistent storage, and read the [browser quota and eviction rules](https://developer.mozilla.org/en-US/docs/Web/API/Storage_API/Storage_quotas_and_eviction_criteria) before promising offline availability.

For an internet-facing product, isolate local inference behind one interface:

```ts
interface LocalRagEngine {
  loadModel(onProgress: (progress: number) => void): Promise<void>
  ingest(files: File[]): Promise<void>
  answer(question: string): AsyncIterable<string>
  clearLocalData(): Promise<void>
}
```

That lets the rest of the app use the same UI whether the implementation is wllama, WebLLM, or an explicitly approved server fallback.

### iOS apps: run the GGUF through llama.cpp and Metal

The direct path is the official [`llama.swiftui`](https://github.com/ggml-org/llama.cpp/tree/master/examples/llama.swiftui) example. Build `llama.cpp` as an XCFramework with `./build-xcframework.sh`, add `llama.xcframework` to the Xcode project, and wrap model loading and token generation behind a Swift actor so inference does not block the main thread.

iOS integration flow:

1. Ship a very small model with the app or download an approved GGUF after installation.
2. Store downloaded weights in application-managed storage and verify their expected hash before loading.
3. Use Metal acceleration through the `llama.cpp` Apple build.
4. Run embedding, retrieval, and generation away from the main actor.
5. Keep the vector store and document text inside the app container unless the user explicitly exports them.
6. Respond to memory pressure by unloading the model instead of letting iOS kill the app.

Apple's [Foundation Models framework](https://developer.apple.com/documentation/FoundationModels/) is another on-device route on supported devices. It uses Apple's model and API rather than this repository's Qwen GGUF path. Treat it as a separate engine behind the same `LocalRagEngine`-style contract, not as a way to load this GGUF unchanged.

### Android apps: use the official Kotlin/native binding

Start with the official [`examples/llama.android`](https://github.com/ggml-org/llama.cpp/tree/master/examples/llama.android) application and [`docs/android.md`](https://github.com/ggml-org/llama.cpp/blob/master/docs/android.md). The example reads GGUF metadata from a `ContentResolver` URI or app-private file, loads the model through its `AiChat` facade, and streams generated tokens as a Kotlin `Flow`.

Android integration flow:

1. Import the `llama.android` example into Android Studio and prove the target model on real low, middle, and high-memory devices.
2. Package the required native libraries for each supported ABI. Do not ship only the build for your development phone.
3. Download the GGUF with WorkManager under explicit network and charging constraints, then verify its hash.
4. Move the approved model into app-private storage before loading it.
5. Keep inference in a lifecycle-aware service or repository, never on the main thread.
6. Stream tokens through `Flow` and expose loading, generating, cancelled, and out-of-memory states to the UI.
7. Tune context size per device tier. The official Android guide warns that an oversized context can spike memory and kill the process.

The native layer can detect supported CPU kernels across newer and older Arm and x86-64 devices. Still benchmark every device tier you claim to support. "Runs on Android" says nothing about time to first token, sustained speed, heat, or memory stability.

### Split mode: local retrieval, remote generation

Some products cannot fit the generator on every device. Keep document parsing, embeddings, and retrieval local, then send only the selected chunks to a private inference endpoint after explicit policy approval.

This reduces data exposure. It does not make the request local. The selected text, question, source metadata, network identifiers, and generated answer still cross the network. Log and disclose that boundary accurately.

### Production controls shared by every platform

- Sign the model manifest and verify each downloaded artifact by hash.
- Version the model, tokenizer, embedding model, chunking rules, prompt, and index schema together.
- Encrypt sensitive local documents using the platform's protected storage and keep keys out of logs.
- Apply document authorization before retrieval, not after generation.
- Treat retrieved documents as untrusted input. Local inference does not stop prompt injection.
- Provide a visible delete action that removes models, indexes, chunks, and conversation history.
- Measure model download size, cold load, first-token latency, tokens per second, peak memory, battery use, and thermal throttling on real devices.
- Keep remote fallback off by default for workflows advertised as private or offline.

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
