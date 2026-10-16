try:
    from pydantic_settings import (
        BaseSettings,
        SettingsConfigDict,
    )
except ImportError:  # pragma: no cover
    from pydantic import BaseSettings  # type: ignore

    SettingsConfigDict = dict


class Settings(
    BaseSettings,
):
    openai_api_key: str | None = None

    agent_model: str = (
        "gpt-4.1-mini"
    )

    # -----------------------------------------------------
    # Phase 3D - document search
    # -----------------------------------------------------

    document_embedding_model: str = (
        "text-embedding-3-small"
    )

    document_retrieval_top_k: int = 6

    document_min_similarity: float = (
        0.30
    )

    supabase_url: str | None = None

    supabase_service_role_key: (
        str | None
    ) = None

    # -----------------------------------------------------
    # Phase 3G-B - financial fact extraction
    # -----------------------------------------------------

    # If unset, the extractor falls back to agent_model.
    fact_extraction_model: str | None = (
        None
    )

    # Financial tables/KPI chunks sometimes have weaker
    # semantic similarity than narrative paragraphs.
    fact_extraction_min_similarity: float = (
        0.20
    )

    # Process several sources per structured-output call
    # rather than sending the entire document at once.
    fact_extraction_batch_sources: int = 6

    # Safety guard for context construction.
    fact_extraction_max_context_chars: int = (
        48000
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    # Serper API settings for web search fallback.
    serper_api_key: str | None = None

    serper_search_enabled: bool = True

    serper_search_url: str = (
        "https://google.serper.dev/search"
    )

    serper_timeout_seconds: float = 12.0

    serper_max_results: int = 8

    serper_language: str = "en"
    # ---------------------------------------------------------
    # Phase 3H-C - safe web source fetching
    # ---------------------------------------------------------

    web_fetch_enabled: bool = True

    web_fetch_timeout_seconds: float = 12.0

    web_fetch_max_redirects: int = 3

    # Maximum number of candidate URLs we will attempt
    # for one web fallback request.
    web_fetch_max_candidates: int = 4

    # Stop early after this many sources contain
    # relevant fetched evidence.
    web_fetch_target_sources: int = 3

    # HTML/text responses are deliberately kept small.
    web_fetch_max_html_bytes: int = 2_000_000

    # PDFs may naturally be larger.
    web_fetch_max_pdf_bytes: int = 12_000_000

    # Protect pypdf from extremely large documents.
    web_fetch_max_pdf_pages: int = 80

    # Maximum extracted text retained internally.
    web_fetch_max_text_chars: int = 500_000

    # Evidence passed to later stages.
    web_evidence_passages_per_source: int = 3

    web_evidence_passage_chars: int = 1600

    # Replace this with a real project/contact identity
    # in .env, especially when accessing SEC.gov.
    web_fetch_user_agent: str = (
        "FinetuningFinance/0.1"
    )

        # ---------------------------------------------------------
    # Phase 3H-E - Structured web financial facts
    # ---------------------------------------------------------

    web_fact_extraction_enabled: bool = True

    web_fact_extraction_model: str | None = None

    web_fact_extraction_max_sources: int = 6

    web_fact_extraction_max_facts: int = 30

    web_fact_extraction_max_context_chars: int = 30000
    
    # =========================================================
    # Phase 3H-F-B
    # Web cost controls
    # =========================================================

    web_max_query_chars: int = 500

    web_max_trusted_domains: int = 10

    web_max_searches_per_user_hour: int = 20

    web_max_results_per_search: int = 8

    # =========================================================
    # Phase 3H-F-C
    # Web caching
    # =========================================================

    web_cache_enabled: bool = True

    # Search-engine discovery changes relatively quickly.
    web_search_cache_ttl_seconds: int = 900

    # Successfully fetched source content can live longer.
    web_fetch_cache_ttl_seconds: int = 3600

    # Maximum entries in each process-local cache.
    web_cache_max_entries: int = 500

    # =========================================================
    # Phase 3I-A
    # Multi-agent contracts / registry guardrails
    # =========================================================

    # Runtime remains disabled until coordinator/DAG/security gates pass.
    multi_agent_enabled: bool = False

    # Initial operational limits. Later 3I-C/3I-D code must read these
    # values rather than introducing duplicate hardcoded limits.
    multi_agent_max_agents_per_request: int = 6
    multi_agent_max_coordinator_rounds: int = 2
    multi_agent_max_retries_per_agent: int = 1
    multi_agent_max_graph_depth: int = 4
    multi_agent_max_web_searches: int = 2
    multi_agent_max_web_fetches: int = 8
    multi_agent_request_timeout_seconds: float = 90.0
    multi_agent_max_concurrency: int = 3

    # Initial development budgets. Tune from provider pricing and telemetry
    # before production rollout; these are guardrails, not billing promises.
    multi_agent_max_llm_tokens: int = 24_000
    multi_agent_max_estimated_cost_usd: float = 0.50

    # Per-agent policy defaults used by the 3I registry.
    multi_agent_default_agent_timeout_seconds: float = 30.0
    multi_agent_web_agent_timeout_seconds: float = 45.0
    multi_agent_default_agent_cost_limit_usd: float = 0.02
    multi_agent_llm_agent_cost_limit_usd: float = 0.15
    multi_agent_web_agent_cost_limit_usd: float = 0.20


    # Phase 3I-H / 3J / 3K rollout flags
    evidence_review_enabled: bool = True
    compliance_blocking_enabled: bool = False
    automation_enabled: bool = False

settings = Settings()
