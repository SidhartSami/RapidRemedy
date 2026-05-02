"""
Rapid Remedy — Vector Index Benchmarking
Compares HNSW vs IVF-Flat on:
  - Index build time
  - Query latency (P50, P95, P99)
  - Recall@10 (vs brute-force ground truth)
  - Memory usage
"""

import time
import statistics
import psycopg2
import numpy as np
from pgvector.psycopg2 import register_vector

# ── Config ────────────────────────────────────────────────────────────────────
DB_CONFIG = dict(host='127.0.0.1', port=5432, dbname='rapidremedy',
                 user='admin', password='admin123')

EMBEDDINGS_PATH = 'embeddings/embeddings.npy'
N_QUERIES       = 100       # number of test queries
TOP_K           = 10        # recall@K
HNSW_M          = 16        # HNSW: max connections per layer
HNSW_EF_CONSTRUCTION = 64  # HNSW: build-time search width
HNSW_EF_SEARCH  = 40       # HNSW: query-time search width
IVF_LISTS       = 100       # IVF: number of clusters (√N is a good default)
IVF_PROBES      = 10        # IVF: clusters to search at query time


# ── Helpers ───────────────────────────────────────────────────────────────────
def get_conn():
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = True
    register_vector(conn)
    return conn


def drop_index(cur, name):
    cur.execute(f"DROP INDEX IF EXISTS {name};")


def get_ground_truth(cur, query_vectors, k):
    """Brute-force exact search (no index) to get ground truth IDs."""
    ground_truth = []
    for qv in query_vectors:
        cur.execute("""
            SELECT id FROM medical_abstracts
            ORDER BY embedding <-> %s::vector
            LIMIT %s
        """, (qv.tolist(), k))
        ids = [row[0] for row in cur.fetchall()]
        ground_truth.append(set(ids))
    return ground_truth


def run_queries(cur, query_vectors, k):
    """Run queries and return (latencies_ms list, result_id_sets list)."""
    latencies = []
    results   = []
    for qv in query_vectors:
        t0 = time.perf_counter()
        cur.execute("""
            SELECT id FROM medical_abstracts
            ORDER BY embedding <-> %s::vector
            LIMIT %s
        """, (qv.tolist(), k))
        rows = cur.fetchall()
        latencies.append((time.perf_counter() - t0) * 1000)
        results.append(set(r[0] for r in rows))
    return latencies, results


def recall_at_k(results, ground_truth):
    scores = []
    for res, gt in zip(results, ground_truth):
        scores.append(len(res & gt) / len(gt))
    return statistics.mean(scores)


def latency_stats(latencies):
    s = sorted(latencies)
    n = len(s)
    return {
        'p50':  s[int(n * 0.50)],
        'p95':  s[int(n * 0.95)],
        'p99':  s[int(n * 0.99)],
        'mean': statistics.mean(s),
    }


def print_results(label, build_time, latencies, recall, index_size_mb=None):
    stats = latency_stats(latencies)
    print(f"\n{'='*55}")
    print(f"  {label}")
    print(f"{'='*55}")
    print(f"  Build time      : {build_time:.2f}s")
    print(f"  Recall@{TOP_K}       : {recall*100:.2f}%")
    print(f"  Latency mean    : {stats['mean']:.2f}ms")
    print(f"  Latency P50     : {stats['p50']:.2f}ms")
    print(f"  Latency P95     : {stats['p95']:.2f}ms")
    print(f"  Latency P99     : {stats['p99']:.2f}ms")
    if index_size_mb:
        print(f"  Index size      : {index_size_mb:.2f}MB")
    print(f"{'='*55}")


def get_index_size_mb(cur, index_name):
    cur.execute("SELECT pg_relation_size(%s) / 1024.0 / 1024.0", (index_name,))
    result = cur.fetchone()
    return result[0] if result else None


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("Loading embeddings from disk...")
    embeddings = np.load(EMBEDDINGS_PATH).astype(np.float32)
    total = len(embeddings)
    print(f"Loaded {total} embeddings of dim {embeddings.shape[1]}")

    # Pick N_QUERIES random vectors as test queries
    rng = np.random.default_rng(42)
    query_idx = rng.choice(total, size=N_QUERIES, replace=False)
    query_vectors = embeddings[query_idx]

    conn = get_conn()
    cur = conn.cursor()

    # ── Ground Truth (brute-force, no index) ──────────────────────────────────
    print(f"\nComputing ground truth with exact search ({N_QUERIES} queries)...")
    drop_index(cur, 'idx_hnsw')
    drop_index(cur, 'idx_ivf')

    t0 = time.perf_counter()
    ground_truth = get_ground_truth(cur, query_vectors, TOP_K)
    exact_latencies, _ = run_queries(cur, query_vectors, TOP_K)
    exact_time = time.perf_counter() - t0
    print_results("EXACT / Brute-Force (Ground Truth)",
                  exact_time, exact_latencies, 1.0)

    # ── HNSW Benchmark ────────────────────────────────────────────────────────
    print(f"\nBuilding HNSW index (m={HNSW_M}, ef_construction={HNSW_EF_CONSTRUCTION})...")
    drop_index(cur, 'idx_hnsw')
    t0 = time.perf_counter()
    cur.execute(f"""
        CREATE INDEX idx_hnsw ON medical_abstracts
        USING hnsw (embedding vector_l2_ops)
        WITH (m = {HNSW_M}, ef_construction = {HNSW_EF_CONSTRUCTION});
    """)
    hnsw_build_time = time.perf_counter() - t0
    print(f"HNSW index built in {hnsw_build_time:.2f}s")

    # Set ef_search for query time
    cur.execute(f"SET hnsw.ef_search = {HNSW_EF_SEARCH};")
    hnsw_latencies, hnsw_results = run_queries(cur, query_vectors, TOP_K)
    hnsw_recall = recall_at_k(hnsw_results, ground_truth)
    hnsw_size   = get_index_size_mb(cur, 'idx_hnsw')
    print_results("HNSW", hnsw_build_time, hnsw_latencies, hnsw_recall, hnsw_size)

    # ── IVF-Flat Benchmark ────────────────────────────────────────────────────
    print(f"\nBuilding IVF-Flat index (lists={IVF_LISTS})...")
    drop_index(cur, 'idx_ivf')
    t0 = time.perf_counter()
    cur.execute(f"""
        CREATE INDEX idx_ivf ON medical_abstracts
        USING ivfflat (embedding vector_l2_ops)
        WITH (lists = {IVF_LISTS});
    """)
    ivf_build_time = time.perf_counter() - t0
    print(f"IVF-Flat index built in {ivf_build_time:.2f}s")

    cur.execute(f"SET ivfflat.probes = {IVF_PROBES};")
    ivf_latencies, ivf_results = run_queries(cur, query_vectors, TOP_K)
    ivf_recall = recall_at_k(ivf_results, ground_truth)
    ivf_size   = get_index_size_mb(cur, 'idx_ivf')
    print_results("IVF-Flat", ivf_build_time, ivf_latencies, ivf_recall, ivf_size)

    # ── Summary Table ─────────────────────────────────────────────────────────
    print("\n")
    print("╔══════════════════════╦══════════════╦══════════════╦══════════════╗")
    print("║ Metric               ║ Exact/BF     ║ HNSW         ║ IVF-Flat     ║")
    print("╠══════════════════════╬══════════════╬══════════════╬══════════════╣")

    def fmt(v, unit='ms'):
        return f"{v:.2f}{unit}".ljust(12)

    es = latency_stats(exact_latencies)
    hs = latency_stats(hnsw_latencies)
    is_ = latency_stats(ivf_latencies)

    print(f"║ Build Time           ║ {'N/A'.ljust(12)} ║ {fmt(hnsw_build_time,'s')} ║ {fmt(ivf_build_time,'s')} ║")
    print(f"║ Recall@{TOP_K}            ║ {'100.00%'.ljust(12)} ║ {(str(round(hnsw_recall*100,2))+'%').ljust(12)} ║ {(str(round(ivf_recall*100,2))+'%').ljust(12)} ║")
    print(f"║ Latency P50          ║ {fmt(es['p50'])} ║ {fmt(hs['p50'])} ║ {fmt(is_['p50'])} ║")
    print(f"║ Latency P95          ║ {fmt(es['p95'])} ║ {fmt(hs['p95'])} ║ {fmt(is_['p95'])} ║")
    print(f"║ Latency P99          ║ {fmt(es['p99'])} ║ {fmt(hs['p99'])} ║ {fmt(is_['p99'])} ║")
    print(f"║ Index Size           ║ {'N/A'.ljust(12)} ║ {fmt(hnsw_size or 0,'MB')} ║ {fmt(ivf_size or 0,'MB')} ║")
    print("╚══════════════════════╩══════════════╩══════════════╩══════════════╝")

    cur.close()
    conn.close()
    print("\nBenchmark complete.")


if __name__ == '__main__':
    main()