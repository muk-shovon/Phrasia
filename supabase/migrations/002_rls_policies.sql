-- RLS policies for Phrasia tables
--
-- Idempotent: DROP POLICY IF EXISTS before each CREATE so this migration
-- can be re-run safely without "policy already exists" errors.

-- Enable RLS on all app tables
alter table documents enable row level security;
alter table document_versions enable row level security;
alter table humanization_jobs enable row level security;
alter table humanization_chunks enable row level security;
alter table provider_configs enable row level security;
alter table provider_usage enable row level security;
alter table paid_authorizations enable row level security;

-- Documents: owner can only see their own
drop policy if exists "owner_reads_own_documents" on documents;
create policy "owner_reads_own_documents"
    on documents for select
    using (auth.uid() = owner_id and is_deleted = false);

drop policy if exists "owner_writes_own_documents" on documents;
create policy "owner_writes_own_documents"
    on documents for insert
    with check (auth.uid() = owner_id);

drop policy if exists "owner_updates_own_documents" on documents;
create policy "owner_updates_own_documents"
    on documents for update
    using (auth.uid() = owner_id);

drop policy if exists "owner_soft_deletes_own_documents" on documents;
create policy "owner_soft_deletes_own_documents"
    on documents for update
    using (auth.uid() = owner_id);

-- Document versions
drop policy if exists "owner_reads_own_versions" on document_versions;
create policy "owner_reads_own_versions"
    on document_versions for select
    using (
        auth.uid() = (select owner_id from documents d where d.id = document_versions.document_id)
    );

drop policy if exists "owner_inserts_own_versions" on document_versions;
create policy "owner_inserts_own_versions"
    on document_versions for insert
    with check (
        auth.uid() = (select owner_id from documents d where d.id = document_versions.document_id)
    );

-- Humanization jobs
drop policy if exists "owner_reads_own_jobs" on humanization_jobs;
create policy "owner_reads_own_jobs"
    on humanization_jobs for select
    using (
        auth.uid() = (select owner_id from documents d where d.id = humanization_jobs.document_id)
    );

drop policy if exists "owner_inserts_own_jobs" on humanization_jobs;
create policy "owner_inserts_own_jobs"
    on humanization_jobs for insert
    with check (
        auth.uid() = (select owner_id from documents d where d.id = humanization_jobs.document_id)
    );

drop policy if exists "owner_updates_own_jobs" on humanization_jobs;
create policy "owner_updates_own_jobs"
    on humanization_jobs for update
    using (
        auth.uid() = (select owner_id from documents d where d.id = humanization_jobs.document_id)
    );

-- Humanization chunks
drop policy if exists "owner_reads_own_chunks" on humanization_chunks;
create policy "owner_reads_own_chunks"
    on humanization_chunks for select
    using (
        auth.uid() = (
            select d.owner_id from humanization_jobs j
            join documents d on d.id = j.document_id
            where j.id = humanization_chunks.job_id
        )
    );

drop policy if exists "owner_inserts_own_chunks" on humanization_chunks;
create policy "owner_inserts_own_chunks"
    on humanization_chunks for insert
    with check (
        auth.uid() = (
            select d.owner_id from humanization_jobs j
            join documents d on d.id = j.document_id
            where j.id = humanization_chunks.job_id
        )
    );

drop policy if exists "owner_updates_own_chunks" on humanization_chunks;
create policy "owner_updates_own_chunks"
    on humanization_chunks for update
    using (
        auth.uid() = (
            select d.owner_id from humanization_jobs j
            join documents d on d.id = j.document_id
            where j.id = humanization_chunks.job_id
        )
    );

-- Provider configs: anyone authenticated can read; only service role writes
drop policy if exists "any_authenticated_reads_providers" on provider_configs;
create policy "any_authenticated_reads_providers"
    on provider_configs for select
    using (auth.role() = 'authenticated');

-- Provider usage: owner reads their own
drop policy if exists "owner_reads_own_usage" on provider_usage;
create policy "owner_reads_own_usage"
    on provider_usage for select
    using (
        auth.uid() = (
            select d.owner_id from humanization_jobs j
            join documents d on d.id = j.document_id
            where j.id = provider_usage.job_id
        )
    );

-- Paid authorizations: owner reads own
drop policy if exists "owner_reads_own_auths" on paid_authorizations;
create policy "owner_reads_own_auths"
    on paid_authorizations for select
    using (
        auth.uid() = (
            select d.owner_id from humanization_jobs j
            join documents d on d.id = j.document_id
            where j.id = paid_authorizations.job_id
        )
    );