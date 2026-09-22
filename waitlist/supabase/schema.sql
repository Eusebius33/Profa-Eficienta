-- Run this once in the Supabase SQL editor (Project -> SQL Editor -> New query)
-- before pointing the Flask app at your project.

create extension if not exists pgcrypto;

create table if not exists waitlist_signups (
  id uuid primary key default gen_random_uuid(),
  email text not null unique,
  tier text not null check (tier in ('free', 'vip')),
  phone text,
  source text,
  stripe_session_id text,
  amount_paid_ron numeric,
  created_at timestamptz not null default now()
);

create index if not exists waitlist_signups_tier_idx on waitlist_signups (tier);

create table if not exists whatsapp_signups (
  id uuid primary key default gen_random_uuid(),
  phone text not null unique,
  source text,
  created_at timestamptz not null default now()
);

-- Row Level Security is enabled with NO policies attached on purpose: this
-- blocks the anon/public key from reading or writing these tables entirely.
-- The Flask backend uses the service_role key, which bypasses RLS, so
-- signups only ever happen through the validated API routes.
alter table waitlist_signups enable row level security;
alter table whatsapp_signups enable row level security;

-- Safe to re-run: if you already created waitlist_signups before phone/
-- Stripe fields existed, this brings an existing table up to date without
-- touching existing rows.
alter table waitlist_signups add column if not exists phone text;
alter table waitlist_signups add column if not exists stripe_session_id text;
alter table waitlist_signups add column if not exists amount_paid_ron numeric;
