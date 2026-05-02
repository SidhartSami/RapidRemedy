# 💊 Rapid-Remedy

Rapid-Remedy is a medical information retrieval system designed to provide quick, reproducible, and reliable insights from the PubMed RCT dataset using modern AI and vector search technologies.

## 🚀 Status Checklist
- [x] **Repo Foundation**: Initialized and structure established.
- [x] **Database**: PostgreSQL with `pgvector` running in Docker.
- [x] **Data Strategy**: Reproducible 7,000-row sample from PubMed 200k created.
- [x] **Environment**: Python `venv` set up with required dependencies.
- [x] **API Connectivity**: Groq Cloud integration for LLM reasoning.
- [x] **Safety**: `.gitignore` configured to prevent accidental large data pushes.

## 🏗️ Project Structure
```text
rapid-remedy/
├── data/               ← PubMed datasets (Raw excluded, Sample included)
├── backend/            ← FastAPI application logic
├── dashboard/          ← Streamlit user interface
├── vector_engine/      ← pgvector indexing and search code
├── docker-compose.yml  ← Database, Backend, and Dashboard orchestration
└── venv/               ← Local development environment
```

## 🛠️ Getting Started

### 1. Database Setup
Ensure Docker is installed and run:
```bash
docker compose up -d db
```
This initializes the `pgvector` foundation.

### 2. Local Environment
Set up your Python environment:
```bash
python -m venv venv
# Windows
.\venv\Scripts\activate
# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Variables
Create a `.env` file in the root directory:
```env
GROQ_API_KEY=your_key_here
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=rapid_remedy
```

## 📊 Data Decision
To ensure reproducibility and performance (especially for embedding generation on 3050Ti GPUs), we use a fixed sample of **7,000 rows** from the PubMed 200k RCT dataset.
- File: `data/working_dataset.csv`
- Random State: `42`

## 👥 Team Workflow
- **Person 1 (Vector Engine)**: Focus on indexing and pgvector optimization.
- **Person 2 (Backend)**: FastAPI endpoints and service logic.
- **Person 3 (Docs/QA)**: SRS, UML, and benchmarking.
- **Person 4 (Frontend)**: Streamlit dashboard and user interaction.

## 🧪 Testing
Run benchmarks and tests via:
```bash
pytest
```