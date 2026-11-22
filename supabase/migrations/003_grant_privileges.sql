-- Migration 003: grant default privileges to Postgres roles
--
-- Context: on a fresh Supabase project the app tables may have no grants
-- for anon / authenticated / service_role, so every request is denied.
-- This migration makes the grants explicit per table. Plain GRANT
-- statements (no dollar-quoted DO blocks) so the SQL editor's
-- semicolon splitter handles them cleanly.
--
-- Run after 001 + 002 via the Supabase SQL Editor (or `supabase db push`).

GRANT SELECT, INSERT, UPDATE, DELETE ON documents TO anon, authenticated, service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON document_versions TO anon, authenticated, service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON humanization_jobs TO anon, authenticated, service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON humanization_chunks TO anon, authenticated, service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON provider_configs TO anon, authenticated, service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON provider_usage TO anon, authenticated, service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON paid_authorizations TO anon, authenticated, service_role;

-- Ensure future tables in public inherit the same defaults
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE TO anon, authenticated, service_role;