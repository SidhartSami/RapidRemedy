"""
Rapid Remedy — Chunking Strategy Benchmark
Compares three chunking strategies on retrieval quality:
  1. Fixed-Size Overlay    : 512 tokens, 10% overlap
  2. Semantic Chunking     : split on medical section headings
  3. Recursive Splitting   : character-based recursive splitting

Metrics per strategy:
  - Avg chunk size (tokens)
  - Chunk count
  - Retrieval Recall@10 vs brute-force ground truth
  - Query latency (P50, P95, P99)
  - Index build time
"""

import re
import time
import statistics
import psycopg2
import numpy as np
import pandas as pd
from pgvector.psycopg2 import register_vector
from sentence_transformers import SentenceTransformer

# ── Config ────────────────────────────────────────────────────────────────────
DB_CONFIG = dict(host='127.0.0.1', port=5432, dbname='rapidremedy',
                 user='admin', password='admin123')

DATA_PATH        = 'data/working_dataset.csv'
N_QUERIES        = 50       # test queries
TOP_K            = 10
FIXED_CHUNK_SIZE = 512      # tokens (approx chars / 4)
FIXED_OVERLAP    = 51       # 10% of 512
RECURSIVE_SIZES  = [512, 256, 128]   # fallback sizes for recursive

# Medical section headings for semantic splitting
MEDICAL_HEADINGS = re.compile(
    r'(?i)(background|objective|methods|results|conclusions?|'
    r'introduction|discussion|purpose|design|setting|patients?|'
    r'interventions?|measurements?|findings?|interpretation|'
    r'contraindications?|dosage|pharmacology|adverse effects?|'
    r'indications?|warnings?|precautions?)',
    re.IGNORECASE
)

MODEL_NAME = 'all-MiniLM-L6-v2'


# ── Chunking Strategies ───────────────────────────────────────────────────────

def fixed_size_chunks(text, chunk_size=FIXED_CHUNK_SIZE, overlap=FIXED_OVERLAP):
    """Split text into fixed-size character chunks with overlap."""
    # Approx: 1 token ≈ 4 chars
    char_size    = chunk_size * 4
    char_overlap = overlap * 4
    chunks = []
    start  = 0
    while start < len(text):
        end = start + char_size
        chunks.append(text[start:end].strip())
        start += char_size - char_overlap
    return [c for c in chunks if len(c) > 50]


def semantic_chunks(text):
    """Split on medical section headings."""
    parts  = MEDICAL_HEADINGS.split(text)
    chunks = []
    i      = 0
    while i < len(parts):
        part = parts[i].strip()
        if MEDICAL_HEADINGS.match(part) and i + 1 < len(parts):
            # heading + its content
            combined = part + ': ' + parts[i + 1].strip()
            if len(combined) > 50:
                chunks.append(combined)
            i += 2
        else:
            if len(part) > 50:
                chunks.append(part)
            i += 1
    # fallback: if no headings found, treat whole text as one chunk
    if not chunks and len(text) > 50:
        chunks = [text.strip()]
    return chunks


def recursive_chunks(text, sizes=None):
    """Recursively split by paragraph → sentence → character."""
    if sizes is None:
        sizes = RECURSIVE_SIZES
    char_size = sizes[0] * 4

    if len(text) <= char_size or len(sizes) == 1:
        return [text.strip()] if len(text.strip()) > 50 else []

    # Try splitting by double newline (paragraphs)
    parts = [p.strip() for p in text.split('\n\n') if p.strip()]
    if len(parts) == 1:
        # Try splitting by sentence
        parts = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
    if len(parts) == 1:
        # Hard split by character size
        return fixed_size_chunks(text, sizes[0], sizes[0] // 10)

    chunks = []
    current = ''
    for part in parts:
        if len(current) + len(part) <= char_size:
            current += ' ' + part
        else:
            if current.strip():
                chunks.append(current.strip())
            # If part itself is too big, recurse with smaller size
            if len(part) > char_size:
                chunks.extend(recursive_chunks(part, sizes[1:]))
            else:
                current = part
    if current.strip():
        chunks.append(current.strip())

    return [c for c in chunks if len(c) > 50]


# ── DB Helpers ────────────────────────────────────────────────────────────────

def get_conn():
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = True
    register_vector(conn)
    return conn


def setup_chunk_table(cur, conn, table_name):
    cur.execute(f"DROP TABLE IF EXISTS {table_name} CASCADE;")
    conn.commit()
    cur.execute(f"""
        CREATE TABLE {table_name} (
            id          SERIAL PRIMARY KEY,
            source_id   VARCHAR(50),
            chunk_idx   INTEGER,
            chunk_text  TEXT,
            embedding   vector(384)
        );
    """)
    conn.commit()

def insert_chunks(cur, table_name, chunks_data, embeddings):
    batch_size = 200
    for i in range(0, len(chunks_data), batch_size):
        batch     = chunks_data[i:i+batch_size]
        batch_emb = embeddings[i:i+batch_size]
        for j, (source_id, chunk_idx, chunk_text) in enumerate(batch):
            cur.execute(f"""
                INSERT INTO {table_name} (source_id, chunk_idx, chunk_text, embedding)
                VALUES (%s, %s, %s, %s)
            """, (source_id, chunk_idx, chunk_text, batch_emb[j].tolist()))


def build_hnsw(cur, table_name, index_name):
    cur.execute(f"DROP INDEX IF EXISTS {index_name};")
    t0 = time.perf_counter()
    cur.execute(f"""
        CREATE INDEX {index_name} ON {table_name}
        USING hnsw (embedding vector_l2_ops)
        WITH (m = 16, ef_construction = 64);
    """)
    return time.perf_counter() - t0


def run_queries(cur, table_name, query_vectors, k):
    latencies = []
    results   = []
    cur.execute(f"SET hnsw.ef_search = 40;")
    for qv in query_vectors:
        t0 = time.perf_counter()
        cur.execute(f"""
            SELECT source_id FROM {table_name}
            ORDER BY embedding <-> %s::vector
            LIMIT %s
        """, (qv.tolist(), k))
        rows = cur.fetchall()
        latencies.append((time.perf_counter() - t0) * 1000)
        results.append(set(r[0] for r in rows))
    return latencies, results


def get_ground_truth(cur, query_vectors, k):
    """Ground truth from original medical_abstracts table (no index)."""
    ground_truth = []
    cur.execute("DROP INDEX IF EXISTS idx_hnsw;")
    for qv in query_vectors:
        cur.execute("""
            SELECT abstract_id FROM medical_abstracts
            ORDER BY embedding <-> %s::vector
            LIMIT %s
        """, (qv.tolist(), k))
        ground_truth.append(set(r[0] for r in cur.fetchall()))
    return ground_truth


def recall_at_k(results, ground_truth):
    scores = []
    for res, gt in zip(results, ground_truth):
        scores.append(len(res & gt) / max(len(gt), 1))
    return statistics.mean(scores)


def latency_stats(latencies):
    s = sorted(latencies)
    n = len(s)
    return {
        'mean': statistics.mean(s),
        'p50':  s[int(n * 0.50)],
        'p95':  s[int(n * 0.95)],
        'p99':  s[int(n * 0.99)],
    }


def print_strategy_results(name, n_chunks, avg_size, build_time, latencies, recall):
    stats = latency_stats(latencies)
    print(f"\n{'='*58}")
    print(f"  Strategy: {name}")
    print(f"{'='*58}")
    print(f"  Total chunks      : {n_chunks}")
    print(f"  Avg chunk size    : {avg_size:.0f} chars (~{avg_size//4:.0f} tokens)")
    print(f"  Index build time  : {build_time:.2f}s")
    print(f"  Recall@{TOP_K}         : {recall*100:.2f}%")
    print(f"  Latency mean      : {stats['mean']:.2f}ms")
    print(f"  Latency P50       : {stats['p50']:.2f}ms")
    print(f"  Latency P95       : {stats['p95']:.2f}ms")
    print(f"  Latency P99       : {stats['p99']:.2f}ms")
    print(f"{'='*58}")


# ── Main ──────────────────────────────────────────────────────────────────────

def benchmark_strategy(strategy_name, table_name, index_name,
                        chunks_data, model, cur, conn,
                        query_vectors, ground_truth):

    print(f"\n[{strategy_name}] Generating embeddings for {len(chunks_data)} chunks...")
    texts      = [c[2] for c in chunks_data]
    embeddings = model.encode(texts, show_progress_bar=True, batch_size=64)
    avg_size   = statistics.mean(len(t) for t in texts)

    print(f"[{strategy_name}] Setting up table...")
    setup_chunk_table(cur, conn, table_name)
    insert_chunks(cur, table_name, chunks_data, embeddings)
    conn.commit()

    print(f"[{strategy_name}] Building HNSW index...")
    build_time = build_hnsw(cur, table_name, index_name)
    conn.commit()

    print(f"[{strategy_name}] Running {N_QUERIES} queries...")
    latencies, results = run_queries(cur, table_name, query_vectors, TOP_K)
    recall = recall_at_k(results, ground_truth)

    print_strategy_results(strategy_name, len(chunks_data),
                           avg_size, build_time, latencies, recall)
    return latency_stats(latencies), recall, len(chunks_data), avg_size, build_time


def main():
    print("Loading dataset...")
    df    = pd.read_csv(DATA_PATH)
    texts = df['abstract_text'].tolist()
    ids   = df['abstract_id'].astype(str).tolist()
    print(f"Loaded {len(texts)} abstracts")

    model = SentenceTransformer(MODEL_NAME)

    # Sample query vectors from original embeddings
    print("Loading base embeddings for query sampling...")
    base_embeddings = np.load('embeddings/embeddings.npy').astype(np.float32)
    rng         = np.random.default_rng(42)
    query_idx   = rng.choice(len(base_embeddings), size=N_QUERIES, replace=False)
    query_vectors = base_embeddings[query_idx]

    conn = get_conn()
    cur  = conn.cursor()

    # Ground truth from original table
    print(f"\nComputing ground truth ({N_QUERIES} queries on original embeddings)...")
    ground_truth = get_ground_truth(cur, query_vectors, TOP_K)

    results_summary = {}

    # ── Strategy 1: Fixed-Size ────────────────────────────────────────────────
    print("\n" + "─"*58)
    print("STRATEGY 1: Fixed-Size Overlay (512 tokens, 10% overlap)")
    print("─"*58)
    fixed_chunks_data = []
    for doc_id, text in zip(ids, texts):
        for idx, chunk in enumerate(fixed_size_chunks(str(text))):
            fixed_chunks_data.append((doc_id, idx, chunk))

    stats, recall, n, avg, bt = benchmark_strategy(
        "Fixed-Size", "chunks_fixed", "idx_fixed_hnsw",
        fixed_chunks_data, model, cur, conn, query_vectors, ground_truth
    )
    results_summary["Fixed-Size"] = (stats, recall, n, avg, bt)

    # ── Strategy 2: Semantic ──────────────────────────────────────────────────
    print("\n" + "─"*58)
    print("STRATEGY 2: Semantic Chunking (medical headings)")
    print("─"*58)
    semantic_chunks_data = []
    for doc_id, text in zip(ids, texts):
        for idx, chunk in enumerate(semantic_chunks(str(text))):
            semantic_chunks_data.append((doc_id, idx, chunk))

    stats, recall, n, avg, bt = benchmark_strategy(
        "Semantic", "chunks_semantic", "idx_semantic_hnsw",
        semantic_chunks_data, model, cur, conn, query_vectors, ground_truth
    )
    results_summary["Semantic"] = (stats, recall, n, avg, bt)

    # ── Strategy 3: Recursive ─────────────────────────────────────────────────
    print("\n" + "─"*58)
    print("STRATEGY 3: Recursive Character Splitting (512→256→128)")
    print("─"*58)
    recursive_chunks_data = []
    for doc_id, text in zip(ids, texts):
        for idx, chunk in enumerate(recursive_chunks(str(text))):
            recursive_chunks_data.append((doc_id, idx, chunk))

    stats, recall, n, avg, bt = benchmark_strategy(
        "Recursive", "chunks_recursive", "idx_recursive_hnsw",
        recursive_chunks_data, model, cur, conn, query_vectors, ground_truth
    )
    results_summary["Recursive"] = (stats, recall, n, avg, bt)

    # ── Final Summary Table ───────────────────────────────────────────────────
    print("\n\n")
    print("╔═══════════════════╦═════════════╦═════════════╦═════════════╗")
    print("║ Metric            ║ Fixed-Size  ║ Semantic    ║ Recursive   ║")
    print("╠═══════════════════╬═════════════╬═════════════╬═════════════╣")

    def col(v, unit=''):
        return f"{v:.2f}{unit}".ljust(11)

    fs = results_summary["Fixed-Size"]
    sm = results_summary["Semantic"]
    rc = results_summary["Recursive"]

    print(f"║ Chunk Count       ║ {str(fs[2]).ljust(11)} ║ {str(sm[2]).ljust(11)} ║ {str(rc[2]).ljust(11)} ║")
    print(f"║ Avg Chunk (chars) ║ {col(fs[3])} ║ {col(sm[3])} ║ {col(rc[3])} ║")
    print(f"║ Build Time        ║ {col(fs[4],'s')} ║ {col(sm[4],'s')} ║ {col(rc[4],'s')} ║")
    print(f"║ Recall@{TOP_K}         ║ {col(fs[1]*100,'%')} ║ {col(sm[1]*100,'%')} ║ {col(rc[1]*100,'%')} ║")
    print(f"║ Latency P50       ║ {col(fs[0]['p50'],'ms')} ║ {col(sm[0]['p50'],'ms')} ║ {col(rc[0]['p50'],'ms')} ║")
    print(f"║ Latency P95       ║ {col(fs[0]['p95'],'ms')} ║ {col(sm[0]['p95'],'ms')} ║ {col(rc[0]['p95'],'ms')} ║")
    print(f"║ Latency P99       ║ {col(fs[0]['p99'],'ms')} ║ {col(sm[0]['p99'],'ms')} ║ {col(rc[0]['p99'],'ms')} ║")
    print("╚═══════════════════╩═════════════╩═════════════╩═════════════╝")

    cur.close()
    conn.close()
    print("\nChunking benchmark complete.")


if __name__ == '__main__':
    main()