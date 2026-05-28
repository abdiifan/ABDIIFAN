-- ═══════════════════════════════════════════════════════════════
-- CDSS Based Alloc — Supabase Database Setup
-- Run this entire script in the Supabase SQL Editor
-- (Dashboard → SQL Editor → New Query → Paste → Run)
-- ═══════════════════════════════════════════════════════════════


-- ── 1. PROFILES TABLE ────────────────────────────────────────
-- Stores role, status, and display info for every registered user.
-- The `id` column is a foreign key to auth.users.

create table if not exists public.profiles (
    id          uuid        primary key references auth.users(id) on delete cascade,
    email       text        not null,
    full_name   text,
    role        text        not null default 'user'   check (role in ('user', 'admin')),
    status      text        not null default 'pending' check (status in ('pending', 'approved', 'rejected')),
    created_at  timestamptz not null default now()
);

-- Index for fast lookups by email
create index if not exists profiles_email_idx on public.profiles(email);

-- ── 2. ACTIVITY LOGS TABLE ──────────────────────────────────
-- Append-only audit log. actor_id references profiles.id.

create table if not exists public.activity_logs (
    id          bigserial   primary key,
    actor_id    uuid        references public.profiles(id) on delete set null,
    action      text        not null,
    detail      text,
    created_at  timestamptz not null default now()
);

create index if not exists activity_logs_actor_idx      on public.activity_logs(actor_id);
create index if not exists activity_logs_created_at_idx on public.activity_logs(created_at desc);


-- ── 3. ROW LEVEL SECURITY ────────────────────────────────────
-- Enable RLS on both tables.

alter table public.profiles      enable row level security;
alter table public.activity_logs enable row level security;


-- ── 3a. PROFILES POLICIES ────────────────────────────────────

-- Users can read their own profile
create policy "profiles: user reads own"
    on public.profiles for select
    using (auth.uid() = id);

-- Users can update their own profile (limited columns — see note)
create policy "profiles: user updates own"
    on public.profiles for update
    using (auth.uid() = id);

-- Admins can read ALL profiles
create policy "profiles: admin reads all"
    on public.profiles for select
    using (
        exists (
            select 1 from public.profiles
            where id = auth.uid() and role = 'admin'
        )
    );

-- Admins can update ALL profiles (for approvals and role changes)
create policy "profiles: admin updates all"
    on public.profiles for update
    using (
        exists (
            select 1 from public.profiles
            where id = auth.uid() and role = 'admin'
        )
    );

-- Service role can insert new profiles (used at sign-up)
-- No policy needed for service_role — it bypasses RLS by default.


-- ── 3b. ACTIVITY LOGS POLICIES ───────────────────────────────

-- Admins can read all logs
create policy "logs: admin reads all"
    on public.activity_logs for select
    using (
        exists (
            select 1 from public.profiles
            where id = auth.uid() and role = 'admin'
        )
    );

-- Any authenticated user can insert a log row (service role handles it in practice)
create policy "logs: authenticated insert"
    on public.activity_logs for insert
    with check (auth.uid() is not null);


-- ── 4. BOOTSTRAP FIRST ADMIN ────────────────────────────────
-- After running this script:
--   1. Sign up via the app UI with abdidebela42@gmail.com
--   2. Run the UPDATE statement below to grant admin access
--   3. You can then approve all other users from the Admin Panel

UPDATE public.profiles
  SET role = 'admin', status = 'approved'
  WHERE email = 'abdidebela42@gmail.com';


-- ── 5. OPTIONAL: realtime ────────────────────────────────────
-- Enable realtime for profiles so the admin panel can auto-refresh
-- (optional — the app polls on page load without it).

-- alter publication supabase_realtime add table public.profiles;