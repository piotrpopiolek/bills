-- ============================================================================
-- Migration: product name embedding on product_indexes
-- ============================================================================
-- Purpose:
--   Enable pgvector and store a product-name embedding beside the trigram index.
--
-- Affected objects:
--   - Extension: vector
--   - Table: product_indexes
--   - Column: product_indexes.embedding vector(768), nullable
--   - Index: idx_product_indexes_embedding_hnsw (hnsw, cosine)
--
-- Existing rows:
--   embedding stays null. No row is deleted or rewritten.
--   A different dimension needs a new migration.
-- ============================================================================

create extension if not exists vector;

alter table product_indexes
    add column embedding vector(768);

comment on column product_indexes.embedding is
    'Product-name embedding, 768 dimensions. Null until computed.';

create index idx_product_indexes_embedding_hnsw
    on product_indexes
    using hnsw (embedding vector_cosine_ops);
