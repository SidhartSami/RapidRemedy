const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, HeadingLevel, LevelFormat, BorderStyle, WidthType,
  ShadingType, VerticalAlign, PageNumber, PageBreak
} = require('docx');
const fs = require('fs');

const BLUE = "1d4ed8";
const LIGHT_BLUE = "dbeafe";
const DARK = "0f172a";
const MID = "475569";
const LIGHT = "f8fafc";
const border = { style: BorderStyle.SINGLE, size: 1, color: "e2e8f0" };
const borders = { top: border, bottom: border, left: border, right: border };

function h1(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    spacing: { before: 400, after: 160 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: BLUE, space: 8 } },
    children: [new TextRun({ text, font: "Arial", size: 32, bold: true, color: DARK })]
  });
}

function h2(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    spacing: { before: 280, after: 120 },
    children: [new TextRun({ text, font: "Arial", size: 26, bold: true, color: BLUE })]
  });
}

function h3(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_3,
    spacing: { before: 200, after: 80 },
    children: [new TextRun({ text, font: "Arial", size: 22, bold: true, color: DARK })]
  });
}

function p(text, opts = {}) {
  return new Paragraph({
    spacing: { before: 60, after: 100 },
    children: [new TextRun({
      text,
      font: "Arial",
      size: 22,
      color: opts.color || MID,
      bold: opts.bold || false,
      italics: opts.italics || false,
    })]
  });
}

function bullet(text, bold_prefix = "") {
  return new Paragraph({
    numbering: { reference: "bullets", level: 0 },
    spacing: { before: 40, after: 40 },
    children: [
      bold_prefix ? new TextRun({ text: bold_prefix, font: "Arial", size: 22, bold: true, color: DARK }) : null,
      new TextRun({ text: bold_prefix ? text : text, font: "Arial", size: 22, color: MID }),
    ].filter(Boolean)
  });
}

function bulletBold(prefix, rest) {
  return new Paragraph({
    numbering: { reference: "bullets", level: 0 },
    spacing: { before: 40, after: 40 },
    children: [
      new TextRun({ text: prefix, font: "Arial", size: 22, bold: true, color: DARK }),
      new TextRun({ text: rest, font: "Arial", size: 22, color: MID }),
    ]
  });
}

function space(before = 200) {
  return new Paragraph({ spacing: { before, after: 0 }, children: [new TextRun("")] });
}

function infoTable(rows) {
  return new Table({
    width: { size: 9360, type: WidthType.DXA },
    columnWidths: [2800, 6560],
    rows: rows.map(([label, value]) => new TableRow({
      children: [
        new TableCell({
          borders,
          width: { size: 2800, type: WidthType.DXA },
          shading: { fill: "f1f5f9", type: ShadingType.CLEAR },
          margins: { top: 80, bottom: 80, left: 140, right: 120 },
          children: [new Paragraph({ children: [new TextRun({ text: label, font: "Arial", size: 20, bold: true, color: DARK })] })]
        }),
        new TableCell({
          borders,
          width: { size: 6560, type: WidthType.DXA },
          margins: { top: 80, bottom: 80, left: 140, right: 120 },
          children: [new Paragraph({ children: [new TextRun({ text: value, font: "Arial", size: 20, color: MID })] })]
        }),
      ]
    }))
  });
}

function benchTable(headers, rows) {
  const colCount = headers.length;
  const totalWidth = 9360;
  const colWidth = Math.floor(totalWidth / colCount);
  const colWidths = headers.map((_, i) => i === 0 ? totalWidth - colWidth * (colCount - 1) : colWidth);

  return new Table({
    width: { size: totalWidth, type: WidthType.DXA },
    columnWidths: colWidths,
    rows: [
      new TableRow({
        tableHeader: true,
        children: headers.map((h, i) => new TableCell({
          borders,
          width: { size: colWidths[i], type: WidthType.DXA },
          shading: { fill: "1d4ed8", type: ShadingType.CLEAR },
          margins: { top: 80, bottom: 80, left: 120, right: 120 },
          children: [new Paragraph({
            alignment: AlignmentType.CENTER,
            children: [new TextRun({ text: h, font: "Arial", size: 18, bold: true, color: "FFFFFF" })]
          })]
        }))
      }),
      ...rows.map((row, ri) => new TableRow({
        children: row.map((cell, ci) => new TableCell({
          borders,
          width: { size: colWidths[ci], type: WidthType.DXA },
          shading: { fill: ri % 2 === 0 ? "FFFFFF" : "f8fafc", type: ShadingType.CLEAR },
          margins: { top: 80, bottom: 80, left: 120, right: 120 },
          children: [new Paragraph({
            alignment: ci === 0 ? AlignmentType.LEFT : AlignmentType.CENTER,
            children: [new TextRun({ text: String(cell), font: "Arial", size: 20, color: MID })]
          })]
        }))
      }))
    ]
  });
}

const doc = new Document({
  numbering: {
    config: [{
      reference: "bullets",
      levels: [{
        level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 720, hanging: 360 } } }
      }]
    }]
  },
  styles: {
    default: { document: { run: { font: "Arial", size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 32, bold: true, font: "Arial" },
        paragraph: { spacing: { before: 400, after: 160 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 26, bold: true, font: "Arial" },
        paragraph: { spacing: { before: 280, after: 120 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 22, bold: true, font: "Arial" },
        paragraph: { spacing: { before: 200, after: 80 }, outlineLevel: 2 } },
    ]
  },
  sections: [{
    properties: {
      page: {
        size: { width: 12240, height: 15840 },
        margin: { top: 1440, right: 1260, bottom: 1440, left: 1260 }
      }
    },
    children: [

      // ── Cover ──────────────────────────────────────────────────────────────
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { before: 1200, after: 80 },
        children: [new TextRun({ text: "Rapid Remedy", font: "Arial", size: 64, bold: true, color: BLUE })]
      }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { before: 0, after: 60 },
        children: [new TextRun({ text: "Product Requirements Document", font: "Arial", size: 28, color: MID })]
      }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { before: 0, after: 600 },
        children: [new TextRun({ text: "Systematic Benchmarking of Vector Search Architectures for Medical Decision Support", font: "Arial", size: 22, italics: true, color: MID })]
      }),

      infoTable([
        ["Version", "1.0"],
        ["Status", "Final — Week 15 Submission"],
        ["Course", "Software Engineering — Spring 2026"],
        ["Institution", "FAST NUCES, Karachi"],
        ["Team", "Hadi Armaghan (23K-0041) · Aliyan Munawwar (23I-0641) · Sidhart Sami (23I-2527) · Abdul Rafy (23P-0560)"],
        ["Focus Area", "Backend Performance Optimization"],
        ["Date", "May 2026"],
      ]),

      space(600),
      new Paragraph({ children: [new PageBreak()] }),

      // ── 1. Executive Summary ───────────────────────────────────────────────
      h1("1. Executive Summary"),
      p("Rapid Remedy is a Retrieval-Augmented Generation (RAG) system built for clinical decision support. A clinician inputs patient symptoms; the system queries a vector database of medical literature (PubMed abstracts, Merck Manuals), retrieves semantically relevant passages, and passes them to a large language model to generate structured clinical suggestions — covering likely conditions, diagnostic procedures, pharmacological interventions, and immediate red flags."),
      p("The project's primary contribution is not just building a working RAG system, but systematically benchmarking retrieval architectures to determine the most efficient configuration for high-stakes medical retrieval — where a false negative can mean a missed diagnosis."),
      space(),

      // ── 2. Problem Statement ───────────────────────────────────────────────
      h1("2. Problem Statement"),
      p("Deploying RAG for healthcare introduces a problem not present in general-purpose applications: the Retrieval Gap. Standard vector databases use Approximate Nearest Neighbor (ANN) search to achieve sub-linear query times, but ANN searches can produce false negatives — missing a life-saving procedure that exists in the database because the approximate search failed to surface it."),
      p("Conversely, exact search guarantees recall but is too slow for real-time clinical use. The engineering problem is: which indexing strategy and retrieval pipeline achieves the best balance of recall and latency for dense medical text?"),
      p("There is currently a lack of empirical data on how chunk size, indexing type (HNSW vs IVF-Flat), and optimization layers (reranking, compression, HyDE, MMR) interact to affect the accuracy of medical recommendations. Rapid Remedy is the benchmark that fills this gap."),
      space(),

      // ── 3. Goals & Non-Goals ──────────────────────────────────────────────
      h1("3. Goals & Non-Goals"),
      h2("3.1 Goals"),
      bulletBold("Benchmark retrieval architectures: ", "Empirically compare HNSW vs IVF-Flat indexing on medical corpora with real latency and recall data."),
      bulletBold("Benchmark chunking strategies: ", "Evaluate fixed-size, semantic, and recursive chunking on retrieval quality."),
      bulletBold("Implement optimization pipeline: ", "Build a composable pipeline of reranking, context compression, HyDE, and MMR that can be toggled independently."),
      bulletBold("Live comparison dashboard: ", "Build a Doctor's Dashboard showing naive vs optimized vs HyDE+MMR pipelines side by side with live benchmark metrics."),
      bulletBold("Quantify tradeoffs: ", "Produce a benchmark report with latency (P99), token usage, and recall data across all configurations."),
      space(120),
      h2("3.2 Non-Goals"),
      bullet("Patient record management — Rapid Remedy is not an EHR system. It retrieves medical literature, not individual patient data."),
      bullet("Definitive diagnosis — the system explicitly disclaims diagnostic authority. It is a clinical decision support tool, not a replacement for physician judgment."),
      bullet("Real-time data — the corpus is a static snapshot of PubMed abstracts. Live medical database updates are out of scope."),
      bullet("Mobile application — the frontend is a web dashboard. Native iOS/Android is not in scope."),
      space(),

      // ── 4. Users ──────────────────────────────────────────────────────────
      h1("4. Target Users"),
      h2("4.1 Primary User"),
      p("Clinicians and medical residents who need rapid access to relevant medical literature for differential diagnosis and treatment planning. They input symptoms and patient context; they receive a structured suggestion with literature backing."),
      h2("4.2 Secondary User"),
      p("Medical informatics researchers and software engineers evaluating RAG architectures for healthcare applications. They use the benchmarking dashboard to compare pipeline performance and understand the latency/recall tradeoffs of different configurations."),
      space(),

      // ── 5. System Architecture ────────────────────────────────────────────
      h1("5. System Architecture"),
      p("Rapid Remedy follows a decoupled microservices architecture with three independent services orchestrated via Docker Compose."),
      space(80),
      benchTable(
        ["Service", "Technology", "Responsibility"],
        [
          ["vector_engine", "Python, Sentence Transformers", "One-time ingestion: generates embeddings, creates pgvector tables, builds HNSW/IVF-Flat indexes"],
          ["backend", "FastAPI, pgvector, Groq", "Serves /query, /health, /stats endpoints. Runs the full RAG pipeline."],
          ["dashboard", "Streamlit, Plotly", "Doctor's Dashboard UI with session history and benchmark charts"],
          ["database", "PostgreSQL + pgvector", "Stores 384-dimensional embeddings and medical abstract metadata"],
        ]
      ),
      space(),

      // ── 6. RAG Pipelines ──────────────────────────────────────────────────
      h1("6. RAG Pipelines"),
      h2("6.1 Naive RAG (Baseline)"),
      p("Raw symptom text is embedded using all-MiniLM-L6-v2 and used to query the vector database via HNSW approximate nearest neighbor search. The top-K results are passed directly to the LLM with no filtering or compression. Serves as the performance baseline."),
      h2("6.2 Optimized RAG"),
      bulletBold("Cross-Encoder Reranking: ", "Retrieves 20 candidates, reranks using cross-encoder/ms-marco-MiniLM-L-6-v2, retains the top 10 by relevance score. Eliminates false positives from vector similarity search."),
      bulletBold("Context Compression: ", "Extracts only sentences from each chunk that are semantically relevant to the query using cosine similarity. Reduces token usage sent to the LLM by 20-30%."),
      bulletBold("Token Budget: ", "Hard cap of 1,500 tokens for the context window. Chunks are packed greedily until the budget is reached."),
      h2("6.3 HyDE + MMR Pipeline"),
      bulletBold("HyDE (Hypothetical Document Embedding): ", "The LLM first generates a hypothetical PubMed-style clinical abstract for the symptoms. That abstract — not the raw query — is embedded and used for retrieval. Bridges the semantic gap between short symptom strings and dense clinical text."),
      bulletBold("MMR (Maximal Marginal Relevance): ", "After retrieval, applies a diversity filter (lambda=0.7) that balances relevance against inter-chunk similarity. Prevents the LLM from receiving near-duplicate abstracts about the same condition."),
      space(),

      // ── 7. Technical Specs ────────────────────────────────────────────────
      h1("7. Technical Specifications"),
      h2("7.1 Indexing Impact Analysis"),
      space(80),
      benchTable(
        ["Index Type", "Search Method", "Construction Time", "Query Latency", "Recall"],
        [
          ["HNSW", "Graph-based ANN", "High (one-time)", "~12ms", "~95% (ANN)"],
          ["IVF-Flat", "Partitioned exact", "Low", "~18ms", "~99% (exact)"],
        ]
      ),
      space(120),
      h2("7.2 Chunking Strategy Comparison"),
      space(80),
      benchTable(
        ["Strategy", "Method", "Chunk Size", "Best For"],
        [
          ["Fixed-Size Overlay", "Token count", "512 tokens, 10% overlap", "General retrieval baseline"],
          ["Semantic Chunking", "Medical headings", "Variable", "Structured clinical documents"],
          ["Recursive Character Splitting", "Character boundaries", "Variable", "Medical tables and mixed content"],
        ]
      ),
      space(120),
      h2("7.3 Embedding & Models"),
      bulletBold("Embedding model: ", "all-MiniLM-L6-v2 (384 dimensions, fast CPU inference)"),
      bulletBold("Reranking model: ", "cross-encoder/ms-marco-MiniLM-L-6-v2"),
      bulletBold("LLM: ", "LLaMA 3.3 70B via Groq API (max_tokens=1024, temperature=0.2)"),
      bulletBold("Vector store: ", "PostgreSQL 15 with pgvector extension"),
      space(),

      // ── 8. Optimization Techniques ────────────────────────────────────────
      h1("8. Optimization Techniques & Design Patterns"),
      h2("8.1 Optimization Pipeline"),
      space(80),
      benchTable(
        ["Technique", "Problem Solved", "Latency Cost", "Quality Gain"],
        [
          ["HNSW Indexing", "Sub-linear search at scale", "~12ms retrieval", "Fast with ~95% recall"],
          ["Cross-Encoder Reranking", "False positives from ANN", "+75ms", "Higher precision"],
          ["Context Compression", "Excessive token usage", "+0ms (CPU)", "20-30% token reduction"],
          ["HyDE", "Short query vs dense text mismatch", "+900ms (LLM call)", "Better recall at scale"],
          ["MMR", "Duplicate chunks in context", "+200ms", "More diverse context"],
        ]
      ),
      space(120),
      h2("8.2 Design Patterns Applied"),
      bulletBold("Strategy Pattern: ", "Index type (HNSW vs IVF-Flat) and chunking strategy are interchangeable at runtime without modifying the retrieval interface."),
      bulletBold("Pipeline Pattern: ", "Each optimization layer (retrieve → rerank → compress → budget → generate) is an independent, composable stage. Any layer can be toggled via API flags."),
      bulletBold("Repository Pattern: ", "pgvector access is abstracted behind a consistent retrieve_chunks() interface regardless of the underlying index type."),
      bulletBold("Microservices Architecture: ", "vector_engine, backend, and dashboard are independently deployable services with no shared state."),
      space(),

      // ── 9. Evaluation Metrics ─────────────────────────────────────────────
      h1("9. Evaluation Metrics (KPIs)"),
      space(80),
      benchTable(
        ["Metric", "Target", "Measurement Method"],
        [
          ["Query Latency (P99)", "<150ms retrieval across 100k vectors", "Automated benchmark script"],
          ["Recall @ 10", "ANN recall vs exact search baseline", "Benchmark script comparing HNSW vs IVF-Flat"],
          ["Token Savings %", ">20% vs naive baseline", "tokens_after / tokens_before"],
          ["Memory Efficiency", "MB per 1,000 indexed abstracts", "Docker stats during ingestion"],
          ["End-to-end Latency", "Full pipeline <2,500ms", "total_latency_ms from API response"],
        ]
      ),
      space(),

      // ── 10. Benchmark Results ─────────────────────────────────────────────
      h1("10. Benchmark Results"),
      p("Results on the medical abstracts dataset with HNSW indexing and semantic chunking:"),
      space(80),
      benchTable(
        ["Pipeline", "Latency (ms)", "Tokens", "Token Savings", "Retrieval (ms)", "HyDE (ms)", "Rerank (ms)", "LLM (ms)"],
        [
          ["Naive RAG", "1,243", "536", "0%", "12.9", "0", "0", "1,229.8"],
          ["Optimized RAG", "1,121", "408", "100%*", "11.8", "0", "75.2", "1,033.5"],
          ["HyDE + MMR", "2,222", "408", "100%*", "35.6", "917", "197.3", "1,071.7"],
        ]
      ),
      space(120),
      p("*Token savings % reflects compression relative to the retrieved candidate set, not the final LLM token count."),
      space(80),
      h2("10.1 Key Findings"),
      bulletBold("Optimized RAG vs Naive: ", "24% reduction in tokens sent to LLM, with a slight latency improvement due to more focused context window reducing LLM processing time."),
      bulletBold("HyDE overhead: ", "HyDE introduces ~900ms overhead (one extra Groq API call for hypothesis generation). At the current dataset size (5k abstracts), it retrieves similar chunks to Optimized RAG. Quality gains are expected at 100k+ vectors where short-query recall becomes a real problem."),
      bulletBold("HNSW vs IVF-Flat: ", "HNSW achieves ~12ms retrieval vs ~18ms for IVF-Flat. IVF-Flat offers higher recall on exact searches at the cost of speed."),
      bulletBold("MMR diversity: ", "With lambda=0.7, MMR balances relevance and diversity effectively. At small dataset sizes, diversity gains are marginal; at scale, this prevents the LLM from receiving redundant context."),
      space(),

      // ── 11. Implementation Roadmap ────────────────────────────────────────
      h1("11. Implementation Roadmap"),
      space(80),
      benchTable(
        ["Phase", "Focus", "Key Deliverables", "Status"],
        [
          ["Research & Setup", "Data Sourcing", "Cleaned PubMed dataset (5k+ abstracts), embedding generation", "Complete"],
          ["Backend Dev", "Vector Database", "pgvector with HNSW/IVF-Flat dual-index, FastAPI server", "Complete"],
          ["Optimization", "Benchmarking", "Reranking, compression, HyDE, MMR layers + automated benchmark scripts", "Complete"],
          ["Frontend", "Dashboard", "Doctor's Dashboard with 3-way pipeline comparison, session history", "Complete"],
          ["Evaluation", "Final Analysis", "Benchmark report, SRS, UML diagrams, test cases", "In Progress"],
        ]
      ),
      space(),

      // ── 12. Resource Requirements ─────────────────────────────────────────
      h1("12. Resource Requirements"),
      h2("12.1 Compute"),
      bulletBold("Language: ", "Python 3.10+"),
      bulletBold("Containerization: ", "Docker + Docker Compose for service orchestration"),
      bulletBold("RAM: ", "8GB+ recommended for model loading (embedding + reranker models)"),
      h2("12.2 Storage"),
      bulletBold("Vector storage: ", "5GB+ for pgvector embeddings and metadata"),
      bulletBold("Dataset: ", "~500MB for 5,000+ PubMed abstracts (working_dataset.csv)"),
      h2("12.3 APIs"),
      bulletBold("Groq API: ", "Free tier sufficient for development. Used for LLM inference (LLaMA 3.3 70B) and HyDE hypothesis generation."),
      space(),

      // ── 13. Future Work ───────────────────────────────────────────────────
      h1("13. Future Work"),
      bulletBold("Patient record integration: ", "Extend the system to query structured patient records (allergies, current medications, history) in addition to medical literature — enabling queries like 'is this patient allergic to X given their record?'"),
      bulletBold("Scale testing: ", "Benchmark at 100k+ vectors to validate HyDE quality gains at production scale."),
      bulletBold("Continuous ingestion: ", "Automated pipeline to ingest new PubMed publications daily, with HNSW index updates without full rebuild."),
      bulletBold("Evaluation dataset: ", "Build a labeled medical QA dataset to measure Recall@10 against ground truth answers, enabling rigorous accuracy benchmarking."),
      bulletBold("Multi-modal retrieval: ", "Incorporate medical imaging metadata and clinical trial data alongside text abstracts."),
      space(400),

      // ── Footer note ───────────────────────────────────────────────────────
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { before: 400, after: 0 },
        border: { top: { style: BorderStyle.SINGLE, size: 2, color: "e2e8f0", space: 12 } },
        children: [new TextRun({ text: "Rapid Remedy · FAST NUCES Karachi · Software Engineering Spring 2026 · For research purposes only", font: "Arial", size: 16, color: "94a3b8", italics: true })]
      }),
    ]
  }]
});

Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync('RapidRemedy_PRD.docx', buf);
  console.log('Done');
});
