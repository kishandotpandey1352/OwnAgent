from langchain_openai import OpenAIEmbeddings
from supabase import Client, create_client

from app.core.config import settings
from app.schemas.tools import (
    DocumentSearchInput,
    DocumentSearchOutput,
    DocumentSource,
)


def _get_supabase_client() -> Client:
    if not settings.supabase_url:
        raise RuntimeError("SUPABASE_URL is required for document search.")

    if not settings.supabase_service_role_key:
        raise RuntimeError(
            "SUPABASE_SERVICE_ROLE_KEY is required for document search."
        )

    return create_client(
        settings.supabase_url,
        settings.supabase_service_role_key,
    )


def _create_query_embedding(query: str) -> list[float]:
    if not settings.openai_api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is required for document search embeddings."
        )

    embeddings = OpenAIEmbeddings(
        model=settings.document_embedding_model,
        api_key=settings.openai_api_key,
    )

    return embeddings.embed_query(query)


def _to_vector_literal(embedding: list[float]) -> str:
    return "[" + ",".join(str(value) for value in embedding) + "]"


def _snippet(text: str, max_chars: int = 900) -> str:
    cleaned = " ".join(text.split())

    if len(cleaned) <= max_chars:
        return cleaned

    return cleaned[:max_chars] + "..."


def document_search_tool(
    user_id: str,
    tool_input: DocumentSearchInput,
) -> DocumentSearchOutput:
    query_embedding = _create_query_embedding(tool_input.query)

    supabase = _get_supabase_client()

    response = supabase.rpc(
        "match_rag_chunks",
        {
            "query_embedding": _to_vector_literal(query_embedding),
            "match_user_id": user_id,
            "match_document_ids": tool_input.document_ids,
            "match_count": tool_input.top_k,
        },
    ).execute()

    rows = response.data or []

    sources = [
        DocumentSource(
            source_number=index + 1,
            document_id=row["document_id"],
            chunk_id=row["chunk_id"],
            file_name=row["file_name"],
            chunk_index=row["chunk_index"],
            page_number=row.get("page_number"),
            score=float(row["score"]),
            snippet=_snippet(row["text"]),
        )
        for index, row in enumerate(rows)
    ]

    return DocumentSearchOutput(
        sources=sources,
        source_count=len(sources),
        best_score=sources[0].score if sources else 0.0,
        embedding_model=settings.document_embedding_model,
    )