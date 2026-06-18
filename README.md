# Docbuck

> A fully-local, multi-stage **Retrieval-Augmented Generation (RAG)** system for private document collections — built with Python 3.12, Qdrant, Ollama, Docling and `fastembed`.

Docbuck ingests heterogeneous documents (PDF, plain text), structures them through a two-tier vector index, and answers natural-language questions over the corpus using locally-hosted LLMs. No data ever leaves the machine.

![Pipeline](resources/docbuck_pipeline.svg)

---

## Why Docbuck

Most RAG demos rely on naive top-k similarity search against a single embedding store, with the LLM left to cope with noisy chunks. Docbuck explores a more disciplined architecture:

- **Two-collection retrieval** — a *Context* collection holds one summary vector per document; a *Universe* collection holds the chunk-level vectors. Search first locates relevant documents, then drills down to the chunks that actually matter.
- **Agentic chain selection** — a lightweight classifier LLM (`qwen2.5:3b`) routes each user request to the most appropriate processing chain (e.g. needle-picking vs. summarization), giving the system room to grow beyond a single retrieval strategy.
- **Structured LLM I/O** — every model interaction that produces metadata (classification, scoring, context extraction) is constrained to a Pydantic-validated JSON schema, removing whole classes of parsing bugs.
- **LLM-graded relevance** — retrieved chunks are re-ranked by an explicit relevance-scoring prompt, not just by cosine distance.
- **Privacy-first** — the entire pipeline (embeddings, LLMs, vector store) runs locally via Ollama and a self-hosted Qdrant; suitable for confidential or regulated documents.

---

## Tech stack

- **Language:** Python 3.12 (uses PEP 695 generics, `Self`, `@override`)
- **LLM runtime:** [Ollama](https://ollama.com) — defaults: `llama3` (chat & summarization), `qwen2.5:3b` (classification & routing)
- **Vector store:** [Qdrant](https://qdrant.tech) (with built-in inference via `models.Document`)
- **Embeddings:** [`fastembed`](https://github.com/qdrant/fastembed) with `intfloat/multilingual-e5-large`
- **Document parsing:** [Docling](https://github.com/DS4SD/docling) + `docling-core` (`HybridChunker`)
- **Schema validation:** Pydantic v2

---

## Getting started

### Prerequisites

- Python **3.12+**
- [Docker](https://docs.docker.com/engine/install/) (for Qdrant) or a Qdrant binary
- [Ollama](https://ollama.com/download) installed and running
- The required Ollama models pulled locally:
  ```bash
  ollama pull llama3
  ollama pull qwen2.5:3b
  ```

### 1. Clone and install dependencies

```bash
git clone <repo-url> docbuck
cd docbuck
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Start Qdrant

```bash
docker compose up -d
```

This exposes the REST API on `:6333` and the gRPC API on `:6334`, with the embedded Dashboard available at <http://localhost:6333/dashboard>.

### 3. Run Docbuck

The CLI entry point is `main.py`:

```bash
python main.py <command> [options]
```

| Command | Description |
|---|---|
| `updoc --path <file-or-dir>` | Ingest a single file or every supported file in a directory. |
| `deldoc --path <file-or-dir>` | Remove the corresponding documents from both collections. |
| `chat` | Interactive REPL — keeps reading prompts until `exit`/`quit`. |
| `query --text "<question>"` | One-shot question against the corpus. |
| `qd --models` | List embedding models supported by `fastembed`. |

#### Example session

```bash
# Ingest a directory of PDFs
python main.py updoc --path ./data/in

# Ask a question
python main.py query --text "How much did I spend on electricity in 2024?"

# Or open a chat
python main.py chat
```

---

## Configuration

All tunables live in `config.py`:

| Setting | Purpose |
|---|---|
| `QDRANT_URL` | Qdrant endpoint (`http://localhost:6333` by default; supports `:memory:` for ephemeral runs). |
| `QD_MODEL_NAME` | Embedding model used by Qdrant's inference layer. |
| `COLLECTION_UNIVERSE` / `COLLECTION_CONTEXT` | Names of the chunk-level and document-level collections. |
| `OL_CHAT_MODEL` | LLM used for final answers and chat. |
| `OL_CLASSIFY_MODEL` | Lightweight LLM for chain routing. |
| `OL_SUMMARIZE_MODEL` | LLM for summarization and most reasoning prompts. |
| `OL_SUMMARIZE_MODEL_CONTEXT_WINDOW` | Used to plan recursive summarization batches for long documents. |
| `OL_CHAT_LANGUAGE` | Language of the user-facing answer. |
| `OL_PROCESSING_LANGUAGE` | Language used for intermediate prompts (queries, summaries, metadata). |
| `LOG_LEVEL`, `LOG_LEVEL_CORTEX`, `LOG_LEVEL_CHAIN` | Per-logger verbosity. |

Initial document categories are seeded from `resources/categories.txt` and grow dynamically as new documents introduce new ones.

---

## Roadmap

- **Summary Chain** — multi-document condensation into a single coherent overview.
- **Aggregation Chain** — calculations, comparisons and synthesis across multiple sources.
- **Chunk metadata** — propagate Docling's structural metadata (page, section, headings) into the *Universe* payload.
- **Document-name awareness** — surface human-readable document names in citations.
- **Adaptive token estimation** — replace the heuristic `len(text) // 3` token estimator with a model-aware tokenizer.
- **Evaluation harness** — automated retrieval/answer-quality metrics on a curated question set.

---

## License

Released under the **Apache License 2.0** — see [`LICENSE`](LICENSE) for the full text.

---

## Author

Built by **Matteo Placenti** as a hands-on exploration of practical RAG architectures, agentic orchestration and local LLM deployment.
