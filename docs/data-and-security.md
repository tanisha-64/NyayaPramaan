# Data and Security Deep Dive

Companion to the [main README](../README.md). This file covers the database schema, the request security flow, the document ingestion pipeline, and the container topology.

- [1. Database schema](#1-database-schema)
- [2. Authentication and security flow](#2-authentication-and-security-flow)
- [3. Document ingestion pipeline](#3-document-ingestion-pipeline)
- [4. Docker container topology](#4-docker-container-topology)

---

## 1. Database Schema

PostgreSQL 15+ on Supabase with the `pgvector` extension.

```mermaid
erDiagram
    users ||--o{ cases : "owns"
    users ||--o{ chat_sessions : "creates"
    users ||--o{ user_game_progress : "tracks"
    cases ||--o{ document_chunks : "contains"
    cases ||--o{ session_documents : "links"
    chat_sessions ||--o{ chat_messages : "contains"
    chat_sessions ||--o{ session_documents : "attaches"

    cases {
        uuid id PK
        uuid user_id FK
        string filename
        string status
        string summary
        string timeline
        int pages_processed
        int total_pages
        string file_url
        datetime created_at
    }

    document_chunks {
        uuid id PK
        uuid case_id FK
        int page_number
        string chunk_text
        string embedding
        datetime created_at
    }

    chat_sessions {
        uuid id PK
        uuid user_id FK
        string title
        uuid case_id FK
        boolean pinned
        datetime updated_at
    }

    chat_messages {
        uuid id PK
        uuid session_id FK
        string role
        string content
        string sources
        datetime created_at
    }

    session_documents {
        uuid id PK
        uuid session_id FK
        uuid case_id FK
        string filename
    }

    statute_sections {
        uuid id PK
        string act
        string act_name
        string section
        string heading
        string source_url
        int page
    }

    section_map {
        string new_act PK
        string new_section
        string old_act
        string old_section
        string subject
        string change_type
    }

    query_log {
        uuid id PK
        string query
        string response
        boolean verified
        string model_used
        string previous_hash
        string entry_hash
        datetime created_at
    }

    user_game_progress {
        uuid id PK
        uuid user_id FK
        int total_points
        int scenarios_completed
        int streak
        int best_streak
    }
```

> **Note on types.** `document_chunks.embedding` is a native `vector(768)` column, `statute_sections` also stores the full provision text, and `section_map` uses a composite primary key of `new_act`, `new_section` and `old_section`. The diagram simplifies these because Mermaid's ER renderer models neither vector types nor composite keys.

### Hash-chained audit ledger

Each row in `query_log` stores `entry_hash = SHA-256(payload + previous_hash)`. Any retrospective edit to an earlier row breaks the chain for every row after it, which `trust_log/hash_chain.py` detects during validation.

### Search RPC functions

| Function | Purpose |
| :--- | :--- |
| `match_document_chunks` | Cosine similarity over one case's chunks |
| `match_document_chunks_multi` | Similarity across several dossiers at once |
| `hybrid_search_judgments` | Vector proximity blended with full-text ranking |
| `hybrid_search_statutes` | Full-text ranking with an exact section-number boost |

Definitions live in `backend/sql/hybrid_search_functions.sql`. After running them, execute `NOTIFY pgrst, 'reload schema';` so the REST API stops serving a stale schema cache.

---

## 2. Authentication and Security Flow

```mermaid
flowchart TD
    Req["Incoming API request"] --> HasJwt{"Bearer JWT present?"}
    HasJwt -->|"no or invalid"| E401["401 Unauthorized"]
    HasJwt -->|"yes"| Verify["Verify token with Supabase Auth"]
    Verify --> Whitelist{"Email present in ADMIN EMAILS?"}
    Whitelist -->|"yes"| RoleAdmin["Role admin"]
    Whitelist -->|"no"| Meta["Read user metadata role"]
    Meta -->|"claims admin"| Demote["Demote to public and block escalation"]
    Meta -->|"professional"| RolePro["Role professional"]
    Meta -->|"public or unset"| RolePublic["Role public"]
    RoleAdmin --> Perm{"Route permitted for this role?"}
    RolePro --> Perm
    RolePublic --> Perm
    Demote --> Perm
    Perm -->|"no"| E403["403 Forbidden"]
    Perm -->|"yes"| Bucket{"Within per user rate limit?"}
    Bucket -->|"no"| E429["429 Too Many Requests with Retry After"]
    Bucket -->|"yes"| Guard["Input guardrail scan for jailbreak patterns"]
    Guard -->|"attack pattern matched"| E400["400 Bad Request, security refusal"]
    Guard -->|"clean"| Run["Execute router workflow"]
```

**Anti-escalation.** Role is never taken from client-controlled metadata alone. A user who sets `{"role": "admin"}` in their own Supabase metadata is demoted to `public` unless their email appears in the server-side `ADMIN_EMAILS` list.

**PII redaction.** `ai_core/guardrails/output_guard.py` masks Aadhaar numbers, PAN numbers, Indian phone numbers and email addresses before a response reaches the user or the audit ledger.

**Secrets.** All credentials come from environment variables. `.env` is gitignored, `.env.example` holds placeholders only, and any key exposed by accident should be rotated rather than merely removed from the history.

---

## 3. Document Ingestion Pipeline

The upload request never waits for indexing. It returns as soon as the summary is ready, and a background worker finishes chunking and embedding while the UI polls for progress.

```mermaid
sequenceDiagram
    autonumber
    actor User as Advocate or citizen
    participant UI as Frontend
    participant Route as document router
    participant Worker as Background worker
    participant Gemini as Gemini OCR
    participant Store as Supabase storage and database

    User->>UI: Selects a file up to 50 MB
    UI->>Route: Upload as multipart form data
    Route->>Gemini: Extract full text
    Route->>Route: Legal domain gate check
    alt Not a legal document
        Route-->>UI: 422 rejection, only legal documents accepted
    end

    Route->>Route: Classify document type
    Route->>Store: Upload raw file to cloud storage
    Route->>Store: Insert case record with status processing
    Route->>Route: Generate fast executive brief and timeline
    Route->>Store: Update case with summary
    Route->>Worker: Dispatch background indexing worker
    Route-->>UI: 200 OK with case id, filename and summary
    Note over UI: User starts reading the summary immediately

    loop While status is processing
        UI->>Route: Poll status every 3 seconds
        Route-->>UI: Pages processed out of total pages
    end

    Worker->>Worker: Chunk document per page with overlap
    Worker->>Gemini: Generate embeddings in batches
    Worker->>Store: Bulk insert document chunks
    Worker->>Store: Update case status to ready

    UI->>Route: Poll status
    Route-->>UI: Status ready with full page count
    Note over UI: Question answering enabled across all pages
```

**Why page numbers are preserved.** Chunking keeps the source page with every chunk, so a cited passage can be traced back to an exact page in the original filing — which is what makes the TrustAgent citation check meaningful rather than decorative.

**Recovery.** If a run is interrupted, the retry-indexing endpoint re-chunks from the stored text without a re-upload.

---

## 4. Docker Container Topology

```mermaid
flowchart LR
    Host(["Host machine"]) -->|"port 3000"| FrontC["Frontend container - node 20 alpine"]
    Host -->|"port 8000"| BackC["Backend container - python 3.11 slim with Tesseract"]
    FrontC -->|"REST calls"| BackC
    BackC --> Supa[("Supabase PostgreSQL and storage")]
    BackC --> AIAPIs["Google Gemini and Groq APIs"]
```

Both containers read the root `.env`. The backend image bundles Tesseract and Poppler so OCR works without external calls when a document cannot be parsed digitally.

```bash
docker compose up --build     # build and start
docker compose up -d          # detached
docker compose down           # stop everything
```

