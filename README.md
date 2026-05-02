<a id="readme-top"></a>

[![Forks][forks-shield]][forks-url]
[![Stars][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]
[![License][license-shield]][license-url]

<br />
<div align="center">
  <h3 align="center">Rapid Remedy</h3>
  <p align="center">
    A benchmarked medical RAG system that retrieves clinical literature and generates structured treatment suggestions from patient symptoms.
    <br />
    <strong>Retrieve · Rerank · Reason</strong>
    <br />
    <br />
    <a href="https://github.com/SidhartSami/RapidRemedy/issues/new?labels=bug&template=bug-report.md">Report Bug</a>
    ·
    <a href="https://github.com/SidhartSami/RapidRemedy/issues/new?labels=enhancement&template=feature-request.md">Request Feature</a>
  </p>
</div>

<details>
  <summary>Table of Contents</summary>
  <ol>
    <li><a href="#about-the-project">About The Project</a></li>
    <li><a href="#rag-pipelines">RAG Pipelines</a></li>
    <li><a href="#optimization-techniques">Optimization Techniques</a></li>
    <li><a href="#technical-design">Technical Design</a></li>
    <li><a href="#built-with">Built With</a></li>
    <li><a href="#getting-started">Getting Started</a></li>
    <li><a href="#benchmark-results">Benchmark Results</a></li>
    <li><a href="#license">License</a></li>
    <li><a href="#contact">Contact</a></li>
  </ol>
</details>

---

## About The Project

Rapid Remedy is a Retrieval-Augmented Generation (RAG) system built for clinical decision support. A doctor inputs patient symptoms — the system searches a vector database of medical abstracts (PubMed, Merck Manuals), retrieves the most relevant literature, and passes it to an LLM to generate a structured clinical suggestion covering likely conditions, diagnostic procedures, pharmacological interventions, and red flags.

The project's core contribution is not just building a working RAG system, but **systematically benchmarking** different retrieval architectures — HNSW vs IVF-Flat indexing, three chunking strategies, and four optimization layers — to determine the most efficient configuration for high-stakes medical retrieval where false negatives can cost lives.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## RAG Pipelines

Rapid Remedy exposes three distinct pipelines, each adding optimization layers over the previous:

### Naive RAG
The baseline. Raw symptom text is embedded using `all-MiniLM-L6-v2` and used to query the vector database with HNSW approximate nearest neighbor search. Top-K results are passed directly to the LLM with no filtering or compression. Serves as the benchmark baseline — fast, but lower precision.

### Optimized RAG
Adds two layers on top of Naive:

- **Cross-Encoder Reranking** — retrieves 20 candidates, reranks all of them using `cross-encoder/ms-marco-MiniLM-L-6-v2`, keeps the top 10 by relevance score. Eliminates false positives that slip through vector similarity.
- **Context Compression** — extracts only the sentences from each chunk that are semantically relevant to the query using cosine similarity. Reduces token usage sent to the LLM by up to 30%.

### HyDE + MMR Pipeline
The most sophisticated configuration:

- **HyDE (Hypothetical Document Embedding)** — instead of embedding the raw symptom string, the system first asks the LLM to generate a hypothetical PubMed-style clinical abstract for those symptoms. That abstract is then embedded and used for retrieval. Short natural-language queries ("chest pain") match poorly against dense clinical text — HyDE bridges this semantic gap.
- **MMR (Maximal Marginal Relevance)** — after retrieval, applies a diversity filter to the candidate chunks. Balances relevance to the query against similarity between already-selected chunks, preventing the LLM from receiving five near-identical abstracts about the same condition.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## Optimization Techniques

| Technique | What It Solves | Latency Cost |
|---|---|---|
| HNSW Indexing | Sub-linear search across 100k+ vectors | ~12ms retrieval |
| Cross-Encoder Reranking | Removes false positives from ANN search | +75ms |
| Context Compression | Cuts token usage sent to LLM | +0ms (CPU only) |
| HyDE | Improves recall for short clinical queries | +900ms (extra LLM call) |
| MMR | Eliminates duplicate chunks in context | +200ms |

The benchmark dashboard lets you compare all three pipelines side by side with live latency breakdowns, token counts, and per-stage timing. The key finding: HyDE improves retrieval quality at significant latency cost — a tradeoff that becomes worthwhile only at scale (100k+ vectors) where short-query recall is a real problem.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## Technical Design

### Architecture
Rapid Remedy follows a **decoupled microservices architecture** with three independent services orchestrated via Docker Compose:

- `vector_engine` — one-time ingestion script that generates embeddings and populates pgvector
- `backend` — FastAPI server exposing `/query`, `/health`, and `/stats` endpoints
- `dashboard` — Streamlit frontend with the Doctor's Dashboard UI

### Vector Database
Medical abstracts are stored in **PostgreSQL with pgvector**. Each abstract is embedded into a 384-dimensional vector using `all-MiniLM-L6-v2`. Two index types are benchmarked:

- **HNSW** (Hierarchical Navigable Small World) — graph-based ANN search. Fast queries (~12ms) but slow index construction. `ef_search=40` is used during query time.
- **IVF-Flat** (Inverted File Index) — partitioned exact search. Higher recall than HNSW at the cost of slightly longer query times.

### Chunking Strategies
Three chunking strategies are evaluated against the medical corpus:

- **Fixed-Size Overlay** — 512-token chunks with 10% overlap. Simple and fast.
- **Semantic Chunking** — splits on medical section headings (Contraindications, Dosage, etc.). Preserves clinical structure.
- **Recursive Character Splitting** — maintains structural integrity of complex medical tables.

### Design Patterns
- **Strategy Pattern** — index type (HNSW vs IVF-Flat) and chunking strategy are swappable at runtime without changing the retrieval interface
- **Pipeline Pattern** — each optimization layer (retrieve → rerank → compress → generate) is an independent, composable stage
- **Repository Pattern** — pgvector access is abstracted behind a consistent retrieval interface regardless of underlying index

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## Built With

* [![Python][Python-badge]][Python-url]
* [![FastAPI][FastAPI-badge]][FastAPI-url]
* [![PostgreSQL][Postgres-badge]][Postgres-url]
* [![Streamlit][Streamlit-badge]][Streamlit-url]
* [![Docker][Docker-badge]][Docker-url]

**Key Technologies:**
- **FastAPI** — Backend API server with async request handling
- **pgvector** — Vector similarity search extension for PostgreSQL
- **Sentence Transformers** — `all-MiniLM-L6-v2` for embeddings, `ms-marco-MiniLM-L-6-v2` cross-encoder for reranking
- **Groq (LLaMA 3.3 70B)** — LLM inference for HyDE hypothesis generation and final clinical suggestion
- **Streamlit + Plotly** — Doctor's Dashboard with live benchmark charts
- **Docker Compose** — Service orchestration for database, backend, and frontend

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## Getting Started

### Prerequisites

- **Docker & Docker Compose** — for running PostgreSQL + pgvector
- **Python 3.10+**
- **Groq API Key** — free at [console.groq.com](https://console.groq.com)

### Installation

1. Clone the repository
   ```sh
   git clone https://github.com/SidhartSami/RapidRemedy.git
   cd rapid-remedy
   ```

2. Configure environment variables
   ```sh
   cp .env.example .env
   # Add your GROQ_API_KEY to .env
   ```

3. Start the database
   ```sh
   docker-compose up -d postgres
   ```

4. Ingest the medical dataset
   ```sh
   # Place working_dataset.csv in /data
   python vector_engine/ingest_init.py
   ```

5. Start the full stack
   ```sh
   docker-compose up
   ```

6. Open the dashboard
   ```
   http://localhost:8501
   ```

### Environment Variables

| Variable | Description |
|---|---|
| `GROQ_API_KEY` | Groq API key for LLM inference |
| `POSTGRES_HOST` | PostgreSQL host (default: `localhost`) |
| `POSTGRES_DB` | Database name (default: `rapidremedy`) |
| `POSTGRES_USER` | Database user (default: `admin`) |
| `POSTGRES_PASSWORD` | Database password |

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## Benchmark Results

Results on a dataset of 5,000+ PubMed medical abstracts:

| Pipeline | Latency (ms) | Tokens | Token Savings |
|---|---|---|---|
| Naive RAG | ~1,243 | ~536 | 0% |
| Optimized RAG | ~1,121 | ~408 | ~24% |
| HyDE + MMR | ~2,222 | ~408 | ~24% |

**Key findings:**
- Optimized RAG reduces token usage by ~24% with a slight latency improvement over Naive due to more focused context
- HyDE adds ~900ms overhead (extra LLM call) with no additional token reduction at small dataset sizes — its retrieval quality gains are expected to emerge at 100k+ vector scale
- HNSW achieves <15ms retrieval latency; IVF-Flat trades ~20% more latency for higher recall on partitioned data

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## License

Distributed under the MIT License. See `LICENSE` for more information.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## Contact

**Hadi Armaghan** — 23K-0041
**Aliyan Munawwar** — 23I-0641
**Sidhart Sami** — 23I-2527
**Abdul Rafy** — 23P-0560

Project: National University of Computer & Emerging Sciences, Karachi — Software Engineering, Spring 2026

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

[forks-shield]: https://img.shields.io/github/forks/SidhartSami/RapidRemedy.svg?style=for-the-badge
[forks-url]: https://github.com/SidhartSami/RapidRemedy/network/members
[stars-shield]: https://img.shields.io/github/stars/SidhartSami/RapidRemedy.svg?style=for-the-badge
[stars-url]: https://github.com/SidhartSami/RapidRemedy/stargazers
[issues-shield]: https://img.shields.io/github/issues/SidhartSami/RapidRemedy.svg?style=for-the-badge
[issues-url]: https://github.com/SidhartSami/RapidRemedy/issues
[license-shield]: https://img.shields.io/github/license/SidhartSami/RapidRemedy.svg?style=for-the-badge
[license-url]: https://github.com/SidhartSami/RapidRemedy/blob/main/LICENSE

[Python-badge]: https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white
[Python-url]: https://python.org/
[FastAPI-badge]: https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white
[FastAPI-url]: https://fastapi.tiangolo.com/
[Postgres-badge]: https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white
[Postgres-url]: https://postgresql.org/
[Streamlit-badge]: https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white
[Streamlit-url]: https://streamlit.io/
[Docker-badge]: https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white
[Docker-url]: https://docker.com/
