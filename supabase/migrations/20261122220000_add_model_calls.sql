-- ============================================================================
-- Migration: log generative and embedding model calls
-- ============================================================================
-- Purpose:
--   Store each model call so a daily generative limit can be counted per user.
--   Embedding calls use the same table and a separate budget.
--
-- Affected objects:
--   - Table: model_calls
--   - Columns: user_id, model, call_kind, tokens, latency_ms, cost, outcome, created_at
--
-- Existing rows:
--   No existing table. Nothing is deleted or rewritten.
-- ============================================================================

create table model_calls (
    id serial primary key,
    user_id integer references users(id) on delete set null,
    model varchar(128) not null,
    call_kind varchar(32) not null,
    tokens integer,
    latency_ms integer not null,
    cost numeric(12, 6) not null,
    outcome varchar(32),
    created_at timestamptz not null default now(),
    constraint model_calls_kind_check check (call_kind in ('generative', 'embedding')),
    constraint model_calls_outcome_check check (
        outcome is null or outcome in ('accepted', 'to_verify', 'rejected')
    )
);

create index idx_model_calls_user_kind_created
    on model_calls (user_id, call_kind, created_at);
