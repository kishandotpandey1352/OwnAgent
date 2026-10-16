create extension if not exists vector;

create table if not exists rag_documents (
  id text primary key,
  user_id text not null,
  file_name text not null,
  file_type text not null,
  kind text not null,
  size bigint not null,
  page_count integer,
  chunk_count integer not null,
  extracted_chars integer not null,
  embedding_model text not null,
  storage_profile text not null,
  created_at timestamptz not null
);

create table if not exists rag_chunks (
  id text primary key,
  user_id text not null,
  document_id text not null references rag_documents(id) on delete cascade,
  file_name text not null,
  chunk_index integer not null,
  text text not null,
  page_number integer,
  token_estimate integer not null,
  char_start integer not null,
  char_end integer not null,
  created_at timestamptz not null
);

create table if not exists rag_vectors (
  id text primary key,
  user_id text not null,
  document_id text not null references rag_documents(id) on delete cascade,
  chunk_id text not null references rag_chunks(id) on delete cascade,
  embedding vector(1536) not null,
  embedding_model text not null,
  created_at timestamptz not null
);

create index if not exists rag_documents_user_id_idx
  on rag_documents(user_id);

create index if not exists rag_chunks_user_document_idx
  on rag_chunks(user_id, document_id);

create index if not exists rag_vectors_user_document_idx
  on rag_vectors(user_id, document_id);

create index if not exists rag_vectors_embedding_idx
  on rag_vectors
  using hnsw (embedding vector_cosine_ops);

create or replace function match_rag_chunks(
  query_embedding vector(1536),
  match_user_id text,
  match_document_ids text[],
  match_count int
)
returns table (
  chunk_id text,
  document_id text,
  file_name text,
  chunk_index int,
  page_number int,
  text text,
  score float
)
language sql
stable
as $$
  select
    c.id as chunk_id,
    c.document_id,
    c.file_name,
    c.chunk_index,
    c.page_number,
    c.text,
    1 - (v.embedding <=> query_embedding) as score
  from rag_vectors v
  join rag_chunks c on c.id = v.chunk_id
  where v.user_id = match_user_id
    and c.user_id = match_user_id
    and (
      match_document_ids is null
      or cardinality(match_document_ids) = 0
      or v.document_id = any(match_document_ids)
    )
  order by v.embedding <=> query_embedding
  limit match_count;
$$;