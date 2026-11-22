-- Migration 001: initial schema for Phrasia
-- NOTE: auth.users is managed by Supabase Auth and already exists.
-- Do not create it here; FKs reference it by schema-qualified name.

create table if not exists documents (
    id uuid primary key default gen_random_uuid(),
    owner_id uuid not null references auth.users(id) on delete cascade,
    title text not null default 'Untitled',
    original_filename text,
    source_type text not null check (source_type in ('pasted_text','txt_upload','docx_upload')),
    language_hint text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    is_deleted boolean not null default false
);

create index if not exists idx_documents_owner on documents(owner_id, is_deleted);

create table if not exists document_versions (
    id uuid primary key default gen_random_uuid(),
    document_id uuid not null references documents(id) on delete cascade,
    version_number integer not null,
    version_type text not null check (version_type in ('original','humanized','manual_edit','imported')),
    content_text text,
    storage_path text,
    content_hash text,
    word_count integer,
    character_count integer,
    created_at timestamptz not null default now(),
    parent_version_id uuid references document_versions(id) on delete set null
);

create index if not exists idx_document_versions_doc on document_versions(document_id, version_number desc);

create table if not exists humanization_jobs (
    id uuid primary key default gen_random_uuid(),
    document_id uuid not null references documents(id) on delete cascade,
    source_version_id uuid not null references document_versions(id),
    result_version_id uuid references document_versions(id),
    status text not null check (status in ('draft','queued','running','pause_requested','paused_user','paused_rate_limit','paused_quota','paused_provider_error','failed','cancelled','completed')),
    mode text not null,
    intensity text not null,
    custom_instruction text,
    preserve_meaning boolean not null default true,
    preserve_facts boolean not null default true,
    preserve_citations boolean not null default true,
    preserve_formatting boolean not null default true,
    provider_mode text not null default 'free_only',
    selected_provider_id text,
    paid_authorization_id uuid,
    total_chunks integer not null default 0,
    completed_chunks integer not null default 0,
    last_error_code text,
    last_error_message_safe text,
    created_at timestamptz not null default now(),
    started_at timestamptz,
    updated_at timestamptz not null default now(),
    completed_at timestamptz
);

create index if not exists idx_humanization_jobs_doc on humanization_jobs(document_id);
create index if not exists idx_humanization_jobs_status on humanization_jobs(status, created_at);

create table if not exists humanization_chunks (
    id uuid primary key default gen_random_uuid(),
    job_id uuid not null references humanization_jobs(id) on delete cascade,
    sequence_index integer not null,
    source_start_offset integer not null default 0,
    source_end_offset integer not null default 0,
    source_text text,
    source_hash text,
    status text not null check (status in ('pending','running','completed','failed','skipped')),
    provider_id text,
    model_id text,
    attempt_count integer not null default 0,
    output_text text,
    input_tokens integer,
    output_tokens integer,
    estimated_cost_usd numeric(12,6),
    provider_request_id text,
    last_error_code text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    completed_at timestamptz
);

create index if not exists idx_humanization_chunks_job on humanization_chunks(job_id, sequence_index);

create table if not exists provider_configs (
    id uuid primary key default gen_random_uuid(),
    provider_id text primary key,
    display_name text not null,
    task_type text not null check (task_type in ('generation','detection','plagiarism')),
    tier_label text not null check (tier_label in ('free','trial','paid','unknown')),
    enabled boolean not null default false,
    priority integer not null default 50,
    default_model text,
    secret_reference text,
    base_url text,
    configuration_json jsonb not null default '{}',
    last_health_status text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists provider_usage (
    id uuid primary key default gen_random_uuid(),
    provider_id text not null references provider_configs(provider_id),
    task_type text,
    job_id uuid references humanization_jobs(id),
    chunk_id uuid references humanization_chunks(id),
    model_id text,
    input_tokens integer,
    output_tokens integer,
    estimated_cost_usd numeric(12,6),
    actual_cost_usd numeric(12,6),
    status_code integer,
    normalized_outcome text,
    created_at timestamptz not null default now()
);

create table if not exists paid_authorizations (
    id uuid primary key default gen_random_uuid(),
    job_id uuid not null references humanization_jobs(id),
    provider_id text not null references provider_configs(provider_id),
    approved_by_owner boolean not null default false,
    approved_at timestamptz,
    estimated_cost_usd numeric(12,6),
    max_cost_usd numeric(12,6) not null default 0,
    authorization_status text not null default 'pending' check (authorization_status in ('pending','approved','rejected','expired'))
);