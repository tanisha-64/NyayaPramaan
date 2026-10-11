# ⚖️ NyayaPramaan (न्यायप्रमाण)
### *Enterprise Verifiable, Citational, & Transparent AI Platform for Indian Law*

[![Next.js](https://img.shields.io/badge/Frontend-Next.js%2015%2B-black?style=flat&logo=next.js)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Supabase](https://img.shields.io/badge/Database-Supabase%20%2B%20pgvector-3ECF8E?style=flat&logo=supabase)](https://supabase.com/)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue?style=flat&logo=python)](https://python.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0-3178C6?style=flat&logo=typescript)](https://www.typescriptlang.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=flat&logo=docker)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 📌 Executive Overview

**NyayaPramaan** is a production-grade, verifiable legal AI platform architected specifically for the Indian legal framework. It encompasses the **Constitution of India**, **Indian Penal Code (IPC)**, **Bharatiya Nyaya Sanhita (BNS)**, **Code of Criminal Procedure (CrPC)**, **Bharatiya Nagarik Suraksha Sanhita (BNSS)**, **Code of Civil Procedure (CPC)**, **Bharatiya Sakshya Adhiniyam (BSA)**, alongside landmark rulings from the **Supreme Court of India** and all State **High Courts**.

The platform prevents legal hallucinations through:
1. **Multi-Document Ingestion & RAG** with zero-block async uploads and live page tracking.
2. **TrustAgent™ Claim-Level Verification** directly anchoring AI statements to statutory citations.
3. **Cryptographic SHA-256 Hash-Chained Audit Ledger** for tamper-evident compliance.
4. **Automated Indian PII Redaction** (Aadhaar, PAN, Phone, Email masking).
5. **3-Tier Multi-Provider LLM Fallbacks** (Google Gemini ➔ Groq ➔ OpenRouter).

---

## 🏛️ Comprehensive System Architecture

```mermaid
graph TD
    User([Citizen / Advocate / Legal Researcher]) -->|Next.js 15 Web Client| Gateway[FastAPI Backend Gateway :8000]
    
    subgraph "1. Safety & Input Guardrails"
        Gateway --> InGuard[Input Guardrail: Jailbreak & Prompt Injection Filter]
        InGuard --> IntentClass[Intent & Audience Classifier]
    end

    subgraph "2. Zero-Blocking Async Ingestion Pipeline"
        Gateway -->|POST /document/upload| QuickResp[Instant 200 OK + Case ID]
        QuickResp --> BgTask[Background Ingestion Worker]
        BgTask --> Storage[Supabase Storage File Upload]
        BgTask --> OCR[Gemini Full-Text OCR / PyPDF Extraction]
        OCR --> Classifier[Multi-Provider Classifier: Keywords + Groq/Gemini/OpenRouter]
        Classifier --> Chunker[Batch Chunker + Live Progress Tracking: 87/152 Pages]
        Chunker --> Summarizer[Case Brief & Timeline Extractor]
        Chunker --> Embedder[Gemini 768-dim Batch Embeddings]
        Embedder --> VectorDB[(Supabase PostgreSQL + pgvector)]
    end

    subgraph "3. Multi-Document Retrieval & CRAG"
        IntentClass -->|Attached Documents| DocRAG[Multi-Doc Similarity Search + Full Text Fallback]
        IntentClass -->|Statute / Case Law Query| KbRAG[Hybrid Dense + Sparse Search on Indian Law KB]
        KbRAG -->|Low Confidence Score| CRAG[Corrective Web Retrieval Search]
    end

    subgraph "4. Multi-Model LLM Gateway & TrustAgent™"
        DocRAG --> LLMGateway[3-Tier LLM Gateway: Gemini ➔ Groq ➔ OpenRouter]
        KbRAG --> LLMGateway
        CRAG --> LLMGateway
        LLMGateway --> DraftAnswer[Draft Legal Analysis]
        DraftAnswer --> ClaimExt[Claim Extractor]
        ClaimExt --> Verifier[Batch Claim Verifier against Retrieved Citations]
        Verifier --> Judge[LLM Self-Reflection & Evaluation Judge]
    end

    subgraph "5. Privacy & Cryptographic Ledger"
        Judge --> OutGuard[Output Guardrail: Aadhaar, PAN, Phone Redaction]
        OutGuard --> HashChain[SHA-256 Hash-Chain Audit Logger]
        HashChain --> FinalResponse[Verified Citational Response + Precedents]
    end

    FinalResponse --> User
```

---

## 🔄 Document Upload & Processing Lifecycle

```mermaid
sequenceDiagram
    autonumber
    actor User as Client (Browser)
    participant API as FastAPI Gateway
    participant BG as Background Worker
    participant Storage as Supabase Storage
    participant Gemini as Gemini AI (OCR & Embeddings)
    participant DB as Supabase DB & pgvector

    User->>API: Upload Document (PDF / DOCX / Scanned)
    API->>DB: Insert Case Record (status: 'processing')
    API-->>User: Instant 200 OK {case_id: '...'} (Zero Wait Time)
    
    API->>BG: Spawn Background Ingestion Task
    BG->>Storage: Upload Raw File to Cloud Storage
    BG->>Gemini: Full-Text Multimodal Extraction & OCR
    BG->>BG: Classify Legal Validity (100+ Legal Citation Patterns)
    
    loop For each page batch
        BG->>Gemini: Generate 768-dim Vector Embeddings
        BG->>DB: Store Document Chunks in pgvector
        BG->>DB: Update Live Progress (e.g. pages_processed=87, total_pages=152)
        User->>API: Poll Status (/document/{case_id}/status)
        API-->>User: Return Live Progress ("Processing 87/152 pages")
    end

    BG->>Gemini: Generate Executive Brief & Timeline
    BG->>DB: Set Case status = 'ready'
    User->>API: Poll Status (/document/{case_id}/status)
    API-->>User: Return status: 'ready' + Summary & Brief
```

---

## 🛡️ TrustAgent™ Claim Verification & Self-Reflection Flow

```mermaid
flowchart TD
    A[Raw Legal Answer from LLM] --> B[Atomic Claim Extractor]
    B -->|Deconstructed Claims| C[Batch Citation & Statutory Verifier]
    C --> D{Evidence Match Evaluation}
    D -->|Direct Statutory Match| E[Mark: VERIFIED]
    D -->|Contextual / Interpretive| F[Mark: PARTIAL]
    D -->|Inconsistent with Statute| G[Mark: CONTRADICTED]
    D -->|No Evidence Found| H[Mark: UNVERIFIED]
    E & F & G & H --> I[LLM Judge & Confidence Scorer]
    I --> J[Helpline & Department Recommendation Engine]
    J --> K[PII Redactor & Hash Chain Logger]
    K --> L[Structured Citational Response Delivered to Client]
```

---

## 👥 Role-Based Access Control (RBAC) Matrix

| Feature / Capability | Public Citizen (`public`) | Advocate / Researcher (`advocate`) | Super Administrator (`superadmin`) |
| :--- | :---: | :---: | :---: |
| **Legal AI Research & Q&A** | ✅ Public Knowledge Base | ✅ Case-Specific + Statutes | ✅ Universal Access |
| **Case Document Ingestion** | Session Temporary | ✅ Persistent Workspaces | ✅ Universal All-User Records |
| **Chronological Timeline & Briefs** | Basic | ✅ Advanced Dossier View | ✅ Advanced Dossier View |
| **Rights Scenario Game & Quiz** | ✅ Full Access | ✅ Full Access | ✅ Full Access |
| **Live Legal News Radar** | ✅ Full Access | ✅ Full Access | ✅ Full Access |
| **Admin Control Panel & Metrics** | ❌ | ❌ | ✅ Full Operations Suite |
| **Tamper-Evident SHA-256 Ledger** | ✅ Read & Verify | ✅ Read & Verify | ✅ Full Audit & Re-indexing |

---

## ✨ Key Features & Capabilities

### 1. ⚡ High-Performance Async Ingestion & Live Progress
- **Instant Response**: Zero-wait file upload. Files of any size (150+ scanned pages) return immediately with a `case_id`.
- **Live UX Tracking**: Real-time progress display in UI (e.g. *"Processing 87/152 pages"*).
- **Multi-Provider Fallback**: Classification uses 100+ Indian legal patterns (AIR, SCR, SCC, High Court formats) and 3 LLM fallbacks (`Groq` ➔ `Gemini` ➔ `OpenRouter`).

### 2. 🛡️ TrustAgent™ Citation Verification
- Deconstructs AI draft responses into discrete factual propositions.
- Validates each proposition against verbatim statutory provisions and judicial records.
- Flags each citation with a trust verdict: `VERIFIED`, `PARTIAL`, `CONTRADICTED`, or `UNVERIFIED`.

### 3. ⛓️ Cryptographic SHA-256 Audit Trail
- Every single query, retrieved evidence block, LLM generation, and verification verdict is cryptographically hashed into an immutable chain (`trust_log/`).
- Verifiable via web interface at `/trust-verification`.

### 4. 🔒 Indian PII Redaction & Enterprise Safety
- Automatic detection and masking of:
  - **Aadhaar Numbers**: `XXXX-XXXX-1234`
  - **PAN Cards**: `ABCDE****F`
  - **Phone Numbers & Email Addresses**
- Multi-tiered jailbreak and prompt-injection defense layers.

---

## 🛠️ Technology Stack

| Layer | Technologies |
|---|---|
| **Frontend** | Next.js 15+ (App Router), React 19, TypeScript, Tailwind CSS, Lucide Icons, Web Speech API |
| **Backend API** | Python 3.11+, FastAPI, Uvicorn, Pydantic v2 |
| **AI / LLM Gateway** | Google Gemini (2.5 & 3.6), Groq (Llama 3.3 70B), OpenRouter (DeepSeek R1), LiteLLM |
| **Vector Database & Auth** | Supabase (PostgreSQL 15+ with `pgvector` extension) |
| **OCR & Document Engine** | Google Gemini Multimodal OCR, Tesseract OCR, PyPDF, pdf2image, python-docx |
| **DevOps & Containers** | Docker, Docker Compose |

---

## 🚀 Quick Start Guide

### Prerequisites
- [Node.js 20+](https://nodejs.org/)
- [Python 3.11+](https://python.org/)
- [Supabase Account](https://supabase.com/) with a PostgreSQL project

---

### Step 1: Clone the Repository
```bash
git clone https://github.com/tanisha-64/NyayaPramaan.git
cd NyayaPramaan
```

---

### Step 2: Supabase Database Setup
1. Open your **Supabase Dashboard** ➔ **SQL Editor**.
2. Run the SQL script from `supabase_schema_updates.sql`:

```sql
-- Enable vector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Cases Table Updates
ALTER TABLE cases ADD COLUMN IF NOT EXISTS filename TEXT;
ALTER TABLE cases ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'processing';
ALTER TABLE cases ADD COLUMN IF NOT EXISTS pages_processed INT DEFAULT 0;
ALTER TABLE cases ADD COLUMN IF NOT EXISTS total_pages INT DEFAULT 0;
ALTER TABLE cases ADD COLUMN IF NOT EXISTS rejection_reason TEXT;
ALTER TABLE cases ADD COLUMN IF NOT EXISTS file_url TEXT;

-- Session Documents Table
CREATE TABLE IF NOT EXISTS session_documents (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  session_id UUID REFERENCES chat_sessions(id) ON DELETE CASCADE,
  case_id UUID REFERENCES cases(id) ON DELETE CASCADE,
  filename TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Multi-document Similarity Search Function
CREATE OR REPLACE FUNCTION match_document_chunks_multi (
  query_embedding vector(768),
  target_case_ids uuid[],
  match_count int default 5
) RETURNS TABLE (
  id uuid,
  case_id uuid,
  page_number int,
  chunk_text text,
  similarity float
)
LANGUAGE sql
STABLE
AS $$
  SELECT
    id,
    case_id,
    page_number,
    chunk_text,
    1 - (embedding <=> query_embedding) AS similarity
  FROM document_chunks
  WHERE case_id = ANY(target_case_ids)
  ORDER BY embedding <=> query_embedding
  LIMIT match_count;
$$;
```

---

### Step 3: Environment Configuration

Create a `.env` file in the root directory:

```env
# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-or-service-role-key

# LLM Providers
GEMINI_API_KEY=your-google-gemini-api-key
GROQ_API_KEY=your-groq-api-key
OPENROUTER_API_KEY=your-openrouter-api-key

# Frontend Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-supabase-anon-key
```

---

### Step 4: Running with Docker (Recommended)

```bash
docker-compose up --build
```
* **Frontend**: [http://localhost:3000](http://localhost:3000)
* **Backend API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

### Step 5: Running Manually (Local Development)

#### Backend:
```bash
# Create and activate virtual environment
python -m venv backend/venv
# Windows:
.\backend\venv\Scripts\activate
# Linux/macOS:
source backend/venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start backend server
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

#### Frontend:
```bash
cd frontend
npm install
npm run dev
```

---

## 📂 Project Directory Structure

```plaintext
NyayaPramaan/
├── ai_core/                    # AI Engine & Multi-Model Orchestration
│   ├── guards/                 # Input/Output Guardrails & PII Redaction
│   ├── rag/                    # Document Chunker, Classifier, Embedder, Multi-Doc RAG
│   ├── llm_gateway.py          # 3-Tier Multi-Provider Fallback Gateway
│   └── trust_agent.py          # Claim Extraction & Citation Verifier
├── backend/                    # FastAPI Application Services
│   ├── routers/                # REST Routers (chat, document, case, admin, quiz, news)
│   ├── services/               # Supabase Database & Storage Client Services
│   ├── Dockerfile              # Backend Container Configuration
│   └── main.py                 # FastAPI Entrypoint & Middleware
├── frontend/                   # Next.js 15+ Frontend Web Application
│   ├── app/                    # Next.js App Router Pages (chat, dashboard, admin, etc.)
│   ├── components/             # Reusable UI Components & Modals
│   ├── hooks/                  # Voice Input, Auth, and Theme Hooks
│   ├── services/               # Frontend API Client Services
│   └── Dockerfile              # Frontend Container Configuration
├── trust_log/                  # Cryptographic SHA-256 Hash-Chain Audit Logs
├── docker-compose.yml          # Container Orchestration
├── requirements.txt            # Python Dependencies
├── supabase_schema_updates.sql # Database Migration Scripts
└── README.md                   # Project Documentation
```

---

## 📜 License

Distributed under the **MIT License**. See `LICENSE` for details.

---

<p align="center">
  <b>NyayaPramaan</b> • <i>Verifiable Legal Intelligence for India</i>
</p>
