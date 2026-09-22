# ⚖️ NyayaPramaan — Comprehensive Step-by-Step Implementation Plan

---

## 📌 Executive Summary
**NyayaPramaan** (न्यायप्रमाण) is an enterprise-grade, verifiable, and transparent AI platform built specifically for the Indian legal ecosystem. It supports the Constitution of India, Bharatiya Nyaya Sanhita (BNS / IPC), Bharatiya Nagarik Suraksha Sanhita (BNSS / CrPC), Code of Civil Procedure (CPC), Bharatiya Sakshya Adhiniyam (BSA), and judgments of the Supreme Court of India & State High Courts.

---

## 🏛️ End-to-End System Architecture

```mermaid
graph TD
    User([User / Citizen / Legal Professional]) -->|Next.js 16 Web Client| FrontApp[Frontend Application]
    FrontApp -->|JWT Authenticated API Calls| FastAPIGateway[FastAPI Backend Gateway :8000]
    
    subgraph "Phase 1: Input Safety & Guardrails"
        FastAPIGateway --> InGuard[Input Guardrail: Jailbreak & Prompt Injection Check]
        InGuard --> IntentClassifier[Adaptive Intent & Audience Classifier]
    end

    subgraph "Phase 2: Ingestion & Document Processing"
        FastAPIGateway --> DocIngest[/document/upload Endpoint]
        DocIngest --> DocClassifier[Document Classifier: Kanoon, Citations & Filenames]
        DocClassifier --> Chunker[PyPDF Fast Extraction + Local OCR Fallback]
        Chunker --> Summarizer[Windowed Case Summarizer & Timeline Extractor]
        Chunker --> Embedder[Gemini Embeddings 768-dim Batch Indexer]
        Embedder --> VectorDB[(Supabase PostgreSQL + pgvector)]
    end

    subgraph "Phase 3: Hybrid Retrieval & CRAG"
        IntentClassifier -->|Attached Documents| DocRAG[Multi-Doc Vector Search + Full-Text Fallback]
        IntentClassifier -->|General Legal Query| KbRAG[Dense + Sparse Hybrid Search on Statutory KB]
        KbRAG -->|Low Confidence / Outdated| CRAG[CRAG Corrective Web Search]
    end

    subgraph "Phase 4: Multi-Model Gateway & TrustAgent™"
        DocRAG --> LLMGateway[3-Tier LLM Gateway: Gemini -> Groq -> OpenRouter]
        KbRAG --> LLMGateway
        CRAG --> LLMGateway
        LLMGateway --> DraftAnswer[Draft Legal Answer]
        DraftAnswer --> ClaimExtractor[Atomic Claim Extractor]
        ClaimExtractor --> BatchVerifier[Batch Claim Verifier against Retrieved Evidence]
        BatchVerifier --> LLMJudge[LLM Self-Reflection & Evaluation Judge]
    end

    subgraph "Phase 5: Privacy Redaction & Cryptographic Audit"
        LLMJudge --> PiiRedactor[Output Guardrail: Aadhaar, PAN, Phone, Email Redaction]
        PiiRedactor --> HashChain[SHA-256 Hash-Chain Audit Logger]
        HashChain --> FinalResponse[Final Verified Citational Response]
    end

    FinalResponse --> FrontApp
```

---

## 🚀 Step-by-Step Implementation Breakdown

### Step 1: Ingestion & Multi-Format Document Intelligence (`ai_core/rag/`)
1. **Document Classifier (`document_classifier.py`)**:
   - Matches Indian Kanoon case laws, High Court / Supreme Court orders, bare acts, FIRs, bail applications, affidavits, deeds, and land dispute dossiers.
   - Evaluates strong legal markers (`AIR`, `SCR`, `SCC`, `Bench:`, `Author:`, `Equivalent citations`, `Article 21`, `Article 19`, `Article 32`, `IPC`, `BNS`, `CrPC`, `BNSS`).
2. **Multi-Source Reader & OCR (`document_reader.py`, `ocr_fallback.py`)**:
   - Digital PDF fast parsing with PyPDF.
   - Scanned page OCR fallback via local Tesseract (zero API quota consumption).
   - Plain text / markdown reading (`.txt`, `.md`, `.json`).
3. **Embeddings & Vector Indexing (`embeddings.py`, `vector_store.py`)**:
   - 768-dimensional dense vectors using Google `gemini-embedding-001`.
   - Batch insertion into Supabase `document_chunks` table with `match_document_chunks_multi` RPC function.
4. **Large-Case Windowing (`summarizer.py`, `extractor.py`)**:
   - Head-and-tail windowing (`[:8000]` + `[-4000:]`) to safely summarize 100+ page judgments (e.g. *A.K. Gopalan vs State of Madras*) without triggering token/rate limits.

### Step 2: Multi-Model LLM Gateway & Fallback Strategy (`ai_core/llm_gateway.py`)
1. **3-Tier Provider Fallback**:
   - Primary: `Gemini 3.6 Flash`
   - Secondary: `Groq (Llama-3.3 / GPT-OSS 20B)`
   - Tertiary: `OpenRouter (DeepSeek R1 Free)`
2. **In-Process Response Caching**:
   - SHA-256 prompt-keyed caching avoids redundant API calls and reduces latency.

### Step 3: TrustAgent™ Claim Verification & Fact Checking (`ai_core/trustagent/`)
1. **Atomic Claim Extraction (`claim_extractor.py`)**:
   - Extracts discrete testable factual propositions from draft responses.
2. **Single-Prompt Batched Verification (`verifier.py`)**:
   - Verifies all claims simultaneously against retrieved legal evidence in a single prompt to conserve token quotas.
   - Assigns verification labels: `verified`, `partial`, `contradicted`, or `unverified`.
3. **Legal Citation & Department Suggestions (`corrector.py`)**:
   - Links statutory authorities and relevant civic helplines.

### Step 4: Safety Guardrails & Cryptographic Audit (`ai_core/guardrails/`, `trust_log/`)
1. **Input Guardrail (`input_guard.py`)**:
   - Blocks prompt injection, jailbreak attempts, and non-legal queries.
2. **Indian PII Redactor (`output_guard.py`)**:
   - Redacts Aadhaar numbers (`XXXX-XXXX-XXXX`), PAN cards (`[A-Z]{5}[0-9]{4}[A-Z]`), phone numbers, and email addresses.
3. **Tamper-Evident SHA-256 Hash Chain (`hash_chain.py`)**:
   - Cryptographically links every query, response, model ID, and verification score.

### Step 5: FastAPI Application Services (`backend/routers/`)
1. `chat_router.py`: Conversation management, multi-document research, full-text context fallback.
2. `document_router.py`: File upload, background worker tasks, cooperative cancellation, status polling.
3. `case_router.py`: Case dossier summaries, structured advocate briefs, and procedural event timelines.
4. `search_router.py`: Precedent search with Court, Authority Type (Binding vs Persuasive), and Year filters.
5. `admin_router.py`, `quiz_router.py`, `news_router.py`, `game_router.py`: Governance, daily quiz, and 24-hour legal news.

### Step 6: Next.js 16 Client & User Experiences (`frontend/`)
1. **Resilient Network API Client (`services/apiClient.ts`)**:
   - Automatic fallback between `http://127.0.0.1:8000` and `http://localhost:8000`.
2. **Citizen AI Research Chat (`/public/chat`)**:
   - Real-time voice search (Web Speech API), document chips, verified citation badges, and takeaway cards.
3. **Professional Advocate Suite (`/app/dashboard`, `/app/cases/[id]`)**:
   - Multi-case dossier library, executive case brief export, and binding SC vs persuasive HC precedent discovery.
4. **Interactive 3D Lady Advocate Guide (*Advocate Nyaya Mitra*)**:
   - 3D perspective entrance, real-time voice narration, audio wave animation, and guided tour.
5. **Civic Gamification & Daily Quiz (`/game`, `/quiz`, `/news`)**:
   - Rights-Rakshak scenario simulator, daily constitutional quiz, and live legal news wire.

---

## 🧪 Verification & Acceptance Testing Plan

```bash
# 1. Run Complete Backend Test Suite
$env:PYTHONPATH="."
python -m pytest tests -v

# 2. Run Frontend Type-Safety and Build Check
cd frontend
npx tsc --noEmit
npm run build
```
