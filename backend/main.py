"""
Rapid Remedy — Optimized RAG Pipeline
Optimizations over naive RAG:
  1. Reranking        : cross-encoder reranks Top-K retrieval results
  2. Context Compression : extract only relevant sentences per chunk
  3. Dynamic Top-K    : drop chunks below relevance threshold
  4. Token Budget     : hard cap context tokens, pack greedily
  5. HyDE             : Hypothetical Document Embedding for better query representation
  6. MMR              : Maximal Marginal Relevance for diverse chunk selection
"""

import os
import re
import time
import psycopg2
import numpy as np
from pgvector.psycopg2 import register_vector
from sentence_transformers import SentenceTransformer, CrossEncoder, util
from groq import Groq
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
DB_CONFIG = dict(
    host=os.getenv("POSTGRES_HOST", "localhost"),
    port=5432,
    dbname=os.getenv("POSTGRES_DB", "rapidremedy"),
    user=os.getenv("POSTGRES_USER", "admin"),
    password=os.getenv("POSTGRES_PASSWORD", "admin123"),
)

GROQ_API_KEY    = os.getenv("GROQ_API_KEY")
GROQ_MODEL      = "llama-3.3-70b-versatile"
EMBED_MODEL     = "all-MiniLM-L6-v2"
RERANK_MODEL    = "cross-encoder/ms-marco-MiniLM-L-6-v2"
INDEX_TABLE     = "medical_abstracts"

# Optimization params
RETRIEVAL_TOP_K     = 20
RERANK_TOP_K        = 10
RELEVANCE_THRESHOLD = 0.0
TOKEN_BUDGET        = 1500
CHARS_PER_TOKEN     = 4

# MMR param — lambda=1.0 means pure relevance (no diversity), 0.0 means pure diversity
MMR_LAMBDA = 0.7

# ── Startup ───────────────────────────────────────────────────────────────────
print("Loading models...")
embedder = SentenceTransformer(EMBED_MODEL)
reranker = CrossEncoder(RERANK_MODEL)

print("Connecting to pgvector...")
conn = psycopg2.connect(**DB_CONFIG)
conn.autocommit = True
register_vector(conn)
cur = conn.cursor()
cur.execute("SET hnsw.ef_search = 40;")

print("Initializing Groq client...")
groq_client = Groq(api_key=GROQ_API_KEY)

app = FastAPI(
    title="Rapid Remedy API",
    description="Optimized Medical RAG",
    version="3.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Schemas ───────────────────────────────────────────────────────────────────
class QueryRequest(BaseModel):
    symptoms: str
    patient_context: str = ""
    top_k: int = 5
    use_reranking: bool = False
    use_compression: bool = False
    use_hyde: bool = False
    use_mmr: bool = False

class RetrievedChunk(BaseModel):
    abstract_id: str
    original_text: str
    compressed_text: str = ""
    score: float
    rerank_score: float = 0.0
    tokens_used: int = 0

class OptimizationStats(BaseModel):
    candidates_retrieved: int
    after_reranking: int
    total_tokens_before: int
    total_tokens_after: int
    final_chunks: int
    token_savings_pct: float
    hyde_hypothesis: str = ""
    mmr_applied: bool = False

class QueryResponse(BaseModel):
    suggestion: str
    chunks: list[RetrievedChunk]
    retrieval_latency_ms: float
    rerank_latency_ms: float = 0.0
    compression_latency_ms: float = 0.0
    hyde_latency_ms: float = 0.0
    mmr_latency_ms: float = 0.0
    llm_latency_ms: float
    total_latency_ms: float
    tokens_used: int
    optimization: OptimizationStats

class HealthResponse(BaseModel):
    status: str
    db: str
    model: str

# ── Helpers ───────────────────────────────────────────────────────────────────
def embed_query(text: str) -> list[float]:
    return embedder.encode([text])[0].tolist()

def retrieve_chunks(query_vec: list[float], k: int) -> list[RetrievedChunk]:
    cur.execute(f"""
        SELECT abstract_id, abstract_text, embedding <-> %s::vector AS score
        FROM {INDEX_TABLE}
        ORDER BY embedding <-> %s::vector
        LIMIT %s
    """, (query_vec, query_vec, k))
    rows = cur.fetchall()
    return [
        RetrievedChunk(abstract_id=str(r[0]), original_text=r[1], score=float(r[2]))
        for r in rows
    ]

def generate_hyde_hypothesis(symptoms: str, patient_context: str) -> str:
    """
    HyDE: Generate a hypothetical medical document that would answer
    the query. We then embed THIS instead of the raw symptom string.
    Short medical queries like 'chest pain' match poorly against
    dense clinical abstracts — a hypothetical abstract bridges that gap.
    """
    hyde_prompt = f"""You are a medical writer. Write a short clinical abstract (3-4 sentences) 
describing the diagnosis, procedures, and treatment for a patient with the following presentation.
Write it in the style of a PubMed abstract — clinical, dense, factual.

Patient Symptoms: {symptoms}
{f'Patient Context: {patient_context}' if patient_context.strip() else ''}

Abstract:"""

    try:
        response = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": hyde_prompt}],
            max_tokens=200,
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"HyDE generation failed: {e}, falling back to raw query")
        return symptoms

def apply_mmr(
    query_vec: list[float],
    chunks: list[RetrievedChunk],
    k: int,
    lambda_param: float = MMR_LAMBDA,
) -> list[RetrievedChunk]:
    """
    MMR: Maximal Marginal Relevance.
    Balances relevance to query vs diversity among selected chunks.
    Prevents the LLM context from being flooded with near-duplicate abstracts.
    
    Score = lambda * relevance_to_query - (1-lambda) * max_similarity_to_selected
    
    lambda=1.0 → pure relevance (same as no MMR)
    lambda=0.5 → equal weight relevance + diversity
    """
    if not chunks or k >= len(chunks):
        return chunks[:k]

    query_tensor = embedder.encode(
        [" ".join(c.original_text.split()[:100]) for c in chunks],
        convert_to_tensor=True
    )
    query_emb = embedder.encode([" ".join(chunks[0].original_text.split()[:10])],
                                 convert_to_tensor=True)

    # Re-embed properly: query vec vs all chunk texts
    chunk_texts = [c.original_text for c in chunks]
    chunk_embs = embedder.encode(chunk_texts, convert_to_tensor=True)
    q_emb = embedder.encode(
        [" ".join(str(v) for v in query_vec[:20])],  # use first 20 dims as proxy text won't work
        convert_to_tensor=True
    )

    # Compute relevance scores (cosine sim to query)
    # We already have distance scores — convert to similarity (lower distance = higher sim)
    relevance_scores = np.array([1.0 / (1.0 + c.score) for c in chunks])

    selected_indices = []
    candidate_indices = list(range(len(chunks)))

    for _ in range(min(k, len(chunks))):
        if not candidate_indices:
            break

        if not selected_indices:
            # First pick: most relevant to query
            best_idx = max(candidate_indices, key=lambda i: relevance_scores[i])
        else:
            # MMR score for each candidate
            best_score = -float("inf")
            best_idx = candidate_indices[0]

            # Get embeddings of selected chunks
            selected_embs = chunk_embs[selected_indices]

            for idx in candidate_indices:
                rel = relevance_scores[idx]

                # Max cosine similarity to any already-selected chunk
                cand_emb = chunk_embs[idx].unsqueeze(0)
                sims = util.cos_sim(cand_emb, selected_embs)[0]
                max_sim = float(sims.max())

                mmr_score = lambda_param * rel - (1 - lambda_param) * max_sim

                if mmr_score > best_score:
                    best_score = mmr_score
                    best_idx = idx

        selected_indices.append(best_idx)
        candidate_indices.remove(best_idx)

    return [chunks[i] for i in selected_indices]

def compress_context(query: str, text: str, threshold: float = 0.2) -> str:
    sentences = re.split(r'(?<=[.!?]) +', text)
    if not sentences:
        return text
        
    query_emb = embedder.encode(query, convert_to_tensor=True)
    sent_embs = embedder.encode(sentences, convert_to_tensor=True)
    cos_scores = util.cos_sim(query_emb, sent_embs)[0]
    
    relevant_sentences = [sentences[i] for i, score in enumerate(cos_scores) if score > threshold]
        
    if not relevant_sentences:
        return sentences[0]
        
    return " ".join(relevant_sentences)

def estimate_tokens(text: str) -> int:
    return len(text) // CHARS_PER_TOKEN

def build_prompt(symptoms: str, patient_context: str, chunks: list[RetrievedChunk]) -> str:
    context_block = "\n\n".join([
        f"[Reference] (ID: {c.abstract_id})\n{c.compressed_text or c.original_text}"
        for c in chunks
    ])

    patient_section = ""
    if patient_context.strip():
        patient_section = f"\nPatient Context:\n{patient_context}\n"

    return f"""You are a clinical decision support assistant. Based on the medical literature provided, suggest relevant medical procedures and pharmacological interventions for the patient's symptoms.

IMPORTANT: Always recommend consulting a licensed physician. Never make a definitive diagnosis.

Patient Symptoms:
{symptoms}
{patient_section}
Relevant Medical Literature:
{context_block}

Based on the above references, provide:
1. Likely conditions to investigate
2. Recommended diagnostic procedures
3. Potential pharmacological interventions
4. Red flags that require immediate attention

Keep your response concise and clinically structured."""

def call_groq(prompt: str) -> tuple[str, int]:
    try:
        response = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1024,
            temperature=0.2,
        )
        text   = response.choices[0].message.content
        tokens = response.usage.total_tokens
        return text, tokens
    except Exception as e:
        print(f"Groq API Error: {e}")
        raise HTTPException(status_code=500, detail=f"Groq LLM Error: {str(e)}")

# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/health", response_model=HealthResponse, tags=["Health"])
def health():
    try:
        cur.execute("SELECT COUNT(*) FROM medical_abstracts;")
        count = cur.fetchone()[0]
        db_status = f"connected ({count} abstracts indexed)"
    except Exception as e:
        db_status = f"error: {str(e)}"
    return HealthResponse(
        status="ok",
        db=db_status,
        model=EMBED_MODEL,
    )

@app.post("/query", response_model=QueryResponse, tags=["RAG"])
def query(req: QueryRequest):
    if not req.symptoms.strip():
        raise HTTPException(status_code=400, detail="symptoms field cannot be empty")

    total_start = time.perf_counter()
    full_query = req.symptoms + " " + req.patient_context

    hyde_ms = 0.0
    hyde_hypothesis = ""

    # ── 0. HyDE (optional) ────────────────────────────────────────────────────
    if req.use_hyde:
        t0 = time.perf_counter()
        hyde_hypothesis = generate_hyde_hypothesis(req.symptoms, req.patient_context)
        # Use the hypothetical document for embedding instead of raw query
        search_text = hyde_hypothesis
        hyde_ms = (time.perf_counter() - t0) * 1000
        print(f"HyDE hypothesis: {hyde_hypothesis[:100]}...")
    else:
        search_text = full_query

    # ── 1. Retrieval ──────────────────────────────────────────────────────────
    t0 = time.perf_counter()
    k = RETRIEVAL_TOP_K if (req.use_reranking or req.use_mmr) else req.top_k
    
    query_vec = embed_query(search_text)
    chunks = retrieve_chunks(query_vec, k)
    retrieval_ms = (time.perf_counter() - t0) * 1000

    if not chunks:
        raise HTTPException(status_code=404, detail="No relevant medical literature found")

    rerank_ms = 0.0
    compression_ms = 0.0
    mmr_ms = 0.0
    total_tokens_before = sum(estimate_tokens(c.original_text) for c in chunks)
    candidates_count = len(chunks)

    # ── 2. Reranking (optional) ───────────────────────────────────────────────
    if req.use_reranking:
        t0 = time.perf_counter()
        pairs = [[full_query, c.original_text] for c in chunks]
        scores = reranker.predict(pairs)
        
        for c, s in zip(chunks, scores):
            c.rerank_score = float(s)
            
        chunks.sort(key=lambda x: x.rerank_score, reverse=True)
        chunks = chunks[:RERANK_TOP_K]
        chunks = [c for c in chunks if c.rerank_score > RELEVANCE_THRESHOLD]
        rerank_ms = (time.perf_counter() - t0) * 1000

    # If no reranking, just take top_k
    if not req.use_reranking and not req.use_mmr:
        chunks = chunks[:req.top_k]

    # ── 3. MMR (optional) ─────────────────────────────────────────────────────
    if req.use_mmr:
        t0 = time.perf_counter()
        chunks = apply_mmr(query_vec, chunks, k=req.top_k, lambda_param=MMR_LAMBDA)
        mmr_ms = (time.perf_counter() - t0) * 1000

    # ── 4. Context Compression & Token Budgeting ──────────────────────────────
    t0 = time.perf_counter()
    final_chunks = []
    current_tokens = 0

    for c in chunks:
        if req.use_compression:
            c.compressed_text = compress_context(full_query, c.original_text, threshold=0.2)
        else:
            c.compressed_text = c.original_text

        c.tokens_used = estimate_tokens(c.compressed_text)
        
        if current_tokens + c.tokens_used <= TOKEN_BUDGET:
            final_chunks.append(c)
            current_tokens += c.tokens_used
        else:
            break

    compression_ms = (time.perf_counter() - t0) * 1000

    total_tokens_after = sum(c.tokens_used for c in final_chunks)
    token_savings_pct = 0.0
    if total_tokens_before > 0:
        token_savings_pct = round((1 - total_tokens_after / total_tokens_before) * 100, 1)

    opt_stats = OptimizationStats(
        candidates_retrieved=candidates_count,
        after_reranking=len(chunks),
        total_tokens_before=total_tokens_before,
        total_tokens_after=total_tokens_after,
        final_chunks=len(final_chunks),
        token_savings_pct=token_savings_pct,
        hyde_hypothesis=hyde_hypothesis,
        mmr_applied=req.use_mmr,
    )

    # ── 5. Prompt & LLM ───────────────────────────────────────────────────────
    prompt = build_prompt(req.symptoms, req.patient_context, final_chunks)
    
    t0 = time.perf_counter()
    suggestion, llm_tokens = call_groq(prompt)
    llm_ms = (time.perf_counter() - t0) * 1000

    total_ms = (time.perf_counter() - total_start) * 1000

    return QueryResponse(
        suggestion=suggestion,
        chunks=final_chunks,
        retrieval_latency_ms=round(retrieval_ms, 2),
        rerank_latency_ms=round(rerank_ms, 2),
        compression_latency_ms=round(compression_ms, 2),
        hyde_latency_ms=round(hyde_ms, 2),
        mmr_latency_ms=round(mmr_ms, 2),
        llm_latency_ms=round(llm_ms, 2),
        total_latency_ms=round(total_ms, 2),
        tokens_used=llm_tokens,
        optimization=opt_stats
    )

@app.get("/stats", tags=["Data"])
def stats():
    cur.execute("SELECT COUNT(*) FROM medical_abstracts;")
    total = cur.fetchone()[0]
    cur.execute("SELECT target, COUNT(*) FROM medical_abstracts GROUP BY target ORDER BY COUNT(*) DESC LIMIT 10;")
    dist = [{"label": r[0], "count": r[1]} for r in cur.fetchall()]
    return {"total_abstracts": total, "label_distribution": dist}