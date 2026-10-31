# Architecture Deep Dive — AI, RAG and Routing

Companion to the [main README](../README.md). This file covers how queries are routed, how the LLM gateway fails over, how old and new statutes are mapped, and how corrective retrieval works.

- [1. Role-based access control](#1-role-based-access-control)
- [2. Multi-tier LLM gateway and circuit breaker](#2-multi-tier-llm-gateway-and-circuit-breaker)
- [3. Section mapping engine](#3-section-mapping-engine)
- [4. Corrective RAG and Self-RAG](#4-corrective-rag-and-self-rag)

---

## 1. Role-Based Access Control

Enforced at the API layer (`backend/auth/supabase_auth.py`) and the UI layer (`frontend/components/auth/RoleGuard.tsx`). Each tier inherits everything from the tier below it.

```mermaid
flowchart TD
    Auth["Supabase authentication - JWT"]
    Auth --> Pub["Public citizen - role public"]
    Auth --> Pro["Legal professional - role professional"]
    Auth --> Adm["Super admin - role admin"]

    Pub --> P1["Bilingual research chat"]
    Pub --> P2["Voice input and output"]
    Pub --> P3["Four guided procedure wizards"]
    Pub --> P4["Rights game, daily quiz and legal news"]

    Pro --> R0["Everything a citizen can do"]
    Pro --> R1["Ingest client case dossiers"]
    Pro --> R2["Executive case briefs"]
    Pro --> R3["Chronological case timeline"]
    Pro --> R4["Precedent search by court and year"]

    Adm --> A0["Everything a professional can do"]
    Adm --> A1["Control tower console"]
    Adm --> A2["Database and LLM health checks"]
    Adm --> A3["IST user analytics"]
    Adm --> A4["Citation accuracy monitoring"]
```

A full feature matrix is in [README section 5](../README.md#5-user-roles-and-workspaces).

---

## 2. Multi-Tier LLM Gateway and Circuit Breaker

`ai_core/llm_gateway.py` wraps three providers behind one `litellm` interface, with an in-memory response cache in front and a circuit breaker per provider.

```mermaid
flowchart TD
    Req["LLM request"] --> Cache{"Response cache hit?"}
    Cache -->|"yes"| Cached["Return cached response in under 5 ms"]
    Cache -->|"no"| Breaker{"Is the provider circuit breaker open?"}
    Breaker --> T1["Tier 1 - Google Gemini Flash"]
    T1 -->|"success"| Done["Return generated answer"]
    T1 -->|"rate limit, auth error or timeout"| T2["Tier 2 - Groq Cloud Llama 3.3"]
    T2 -->|"success"| Done
    T2 -->|"failure"| T3["Tier 3 - OpenRouter backup"]
    T3 -->|"success"| Done
    T3 -->|"failure"| Refuse["Graceful message - service busy, try again shortly"]
    T1 -.->|"disable provider for 60 seconds"| Breaker
    T2 -.->|"disable provider for 60 seconds"| Breaker
```

**Caching.** Prompt and model are hashed into a SHA-256 key. The cache is thread-safe and holds up to 256 responses, so repeated questions inside a session return almost instantly.

**Circuit breaker.** A provider that returns an auth error, HTTP 429 or timeout is disabled for 60 seconds (`BREAKER_SECS = 60`). Traffic moves straight to the next tier instead of paying the failure latency on every request.

---

## 3. Section Mapping Engine

`ai_core/rag/section_map.py` resolves provisions in both directions using a database table loaded from `data/section_map.csv` (1,316 verified transitions), and applies the 1 July 2024 cut-off rule.

```mermaid
flowchart LR
    subgraph Legacy["Legacy codes - offences before 1 July 2024"]
        IPC["Indian Penal Code 1860"]
        CrPC["Code of Criminal Procedure 1973"]
        IEA["Indian Evidence Act 1872"]
    end

    subgraph Engine["Deterministic section map engine"]
        Lookup["Lookup by act and section"]
        Cutoff{"Offence date before 1 July 2024?"}
        Change["Classify change type"]
    end

    subgraph Modern["Modern Sanhitas - offences on or after 1 July 2024"]
        BNS["Bharatiya Nyaya Sanhita 2023"]
        BNSS["Bharatiya Nagarik Suraksha Sanhita 2023"]
        BSA["Bharatiya Sakshya Adhiniyam 2023"]
    end

    IPC --> Lookup
    CrPC --> Lookup
    IEA --> Lookup
    BNS --> Lookup
    BNSS --> Lookup
    BSA --> Lookup
    Lookup --> Cutoff
    Cutoff -->|"before"| ApplyOld["Apply legacy provision"]
    Cutoff -->|"on or after"| ApplyNew["Apply new Sanhita provision"]
    ApplyOld --> Change
    ApplyNew --> Change
    Change --> Result["Return mapped section with NO CHANGE, MODIFIED or NEW"]
```

**Worked example.** For *"What is Section 302 IPC?"* the engine returns the IPC provision with its applicability window, the BNS equivalent (**Section 103 BNS**), the change type, and the official India Code source link.

---

## 4. Corrective RAG and Self-RAG

When internal retrieval is weak, the system searches the open web — but only within a strict allowlist of official and reputable legal domains, and only after stripping PII from the query.

```mermaid
flowchart TD
    Query["User query"] --> Embed["Embed with Gemini 768 dimensions"]
    Embed --> Retrieve["Retrieve internal candidates"]
    Retrieve --> Score{"Best similarity at least 0.55?"}
    Score -->|"yes"| Window["Build evidence window"]
    Score -->|"no"| Redact["Redact PII from search terms"]
    Redact --> Web["Bounded web search, maximum 3 attempts"]
    Web --> HostCheck{"Hostname allowlist check"}
    HostCheck -->|"gov.in or nic.in"| Tier1["Tier 1 - primary authority"]
    HostCheck -->|"livelaw, barandbench, indiankanoon"| Tier2["Tier 2 - legal commentary"]
    HostCheck -->|"anything else"| Drop["Discard result"]
    Tier1 --> Window
    Tier2 --> Window
    Window --> Gw["Multi provider LLM gateway"]
    Gw --> Raw["Draft legal answer"]
    Raw --> Self["Self-RAG reflection step"]
    Self --> Useful["Rate usefulness as high, medium or low"]
    Self --> Brief{"Is the answer already brief?"}
    Brief -->|"yes"| Skip["Omit redundant conclusion box"]
    Brief -->|"no"| Attach["Attach highlighted takeaway"]
```

**Why the allowlist matters.** Legal misinformation is abundant on forums and content farms. Restricting corrective retrieval to government portals and established legal publications keeps the evidence window citable, and anything outside the allowlist is discarded rather than down-ranked.

**Self-RAG.** After drafting, the model critiques its own answer: it rates usefulness, extracts a one-sentence bottom line, and suppresses the takeaway box when the answer is already short enough that a summary would be redundant.

