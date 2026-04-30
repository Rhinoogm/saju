create extension if not exists "pgcrypto";

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  email text,
  display_name text,
  avatar_url text,
  provider text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.products (
  code text primary key,
  name text not null,
  amount_krw integer not null check (amount_krw > 0),
  currency text not null default 'KRW',
  active boolean not null default true,
  created_at timestamptz not null default now()
);

insert into public.products(code, name, amount_krw, currency, active)
values ('SAJU_FULL_READING', '사주 심화 리딩 1회권', 9900, 'KRW', true)
on conflict (code) do update set
  name = excluded.name,
  amount_krw = excluded.amount_krw,
  currency = excluded.currency,
  active = excluded.active;

create table if not exists public.orders (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  product_code text not null references public.products(code),
  payment_id text not null unique,
  portone_tx_id text,
  order_name text not null,
  amount_krw integer not null check (amount_krw > 0),
  currency text not null default 'KRW',
  status text not null check (
    status in (
      'ready',
      'payment_requested',
      'paid',
      'failed',
      'cancelled',
      'refunded',
      'expired',
      'verification_failed'
    )
  ) default 'ready',
  failure_reason text,
  raw_payment jsonb,
  paid_at timestamptz,
  cancelled_at timestamptz,
  refunded_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.payment_events (
  id uuid primary key default gen_random_uuid(),
  webhook_id text unique,
  payment_id text not null,
  event_type text not null,
  raw_event jsonb not null,
  processed_at timestamptz not null default now()
);

create table if not exists public.reading_sessions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  order_id uuid references public.orders(id),
  status text not null check (
    status in (
      'payment_required',
      'paid',
      'fixed_questions_ready',
      'custom_questions_ready',
      'final_ready',
      'failed'
    )
  ) default 'payment_required',
  reading_style text not null default 'traditional' check (reading_style in ('traditional', 'empathetic', 'direct')),
  initial_profile jsonb not null,
  fixed_questions jsonb,
  fixed_answers jsonb,
  custom_questions jsonb,
  custom_answers jsonb,
  final_result jsonb,
  error_message text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.reading_credits (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  order_id uuid not null unique references public.orders(id) on delete cascade,
  status text not null check (status in ('available', 'consumed', 'refunded')) default 'available',
  consumed_by_session_id uuid unique references public.reading_sessions(id),
  created_at timestamptz not null default now(),
  consumed_at timestamptz
);

create table if not exists public.admin_members (
  user_id uuid primary key references auth.users(id) on delete cascade,
  role text not null check (role in ('admin', 'owner')),
  created_at timestamptz not null default now()
);

create table if not exists public.admin_audit_logs (
  id uuid primary key default gen_random_uuid(),
  actor_user_id uuid not null references auth.users(id),
  action text not null,
  target text not null,
  before_value jsonb,
  after_value jsonb,
  created_at timestamptz not null default now()
);

create index if not exists orders_user_id_created_at_idx on public.orders(user_id, created_at desc);
create index if not exists reading_sessions_user_id_created_at_idx on public.reading_sessions(user_id, created_at desc);
create index if not exists reading_sessions_order_id_idx on public.reading_sessions(order_id);
create index if not exists reading_credits_user_id_status_idx on public.reading_credits(user_id, status);
create index if not exists payment_events_payment_id_idx on public.payment_events(payment_id);

drop trigger if exists profiles_set_updated_at on public.profiles;
create trigger profiles_set_updated_at
before update on public.profiles
for each row execute procedure public.set_updated_at();

drop trigger if exists orders_set_updated_at on public.orders;
create trigger orders_set_updated_at
before update on public.orders
for each row execute procedure public.set_updated_at();

drop trigger if exists reading_sessions_set_updated_at on public.reading_sessions;
create trigger reading_sessions_set_updated_at
before update on public.reading_sessions
for each row execute procedure public.set_updated_at();

alter table public.profiles enable row level security;
alter table public.products enable row level security;
alter table public.orders enable row level security;
alter table public.payment_events enable row level security;
alter table public.reading_sessions enable row level security;
alter table public.reading_credits enable row level security;
alter table public.admin_members enable row level security;
alter table public.admin_audit_logs enable row level security;

drop policy if exists profiles_select_own on public.profiles;
create policy profiles_select_own
on public.profiles for select
to authenticated
using ((select auth.uid()) = id);

drop policy if exists profiles_update_own on public.profiles;
create policy profiles_update_own
on public.profiles for update
to authenticated
using ((select auth.uid()) = id)
with check ((select auth.uid()) = id);

drop policy if exists products_select_active on public.products;
create policy products_select_active
on public.products for select
to anon, authenticated
using (active = true);

drop policy if exists orders_select_own on public.orders;
create policy orders_select_own
on public.orders for select
to authenticated
using ((select auth.uid()) = user_id);

drop policy if exists reading_sessions_select_own on public.reading_sessions;
create policy reading_sessions_select_own
on public.reading_sessions for select
to authenticated
using ((select auth.uid()) = user_id);

drop policy if exists reading_credits_select_own on public.reading_credits;
create policy reading_credits_select_own
on public.reading_credits for select
to authenticated
using ((select auth.uid()) = user_id);

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer set search_path = public
as $$
begin
  insert into public.profiles (id, email, display_name, avatar_url, provider)
  values (
    new.id,
    new.email,
    coalesce(new.raw_user_meta_data ->> 'full_name', new.raw_user_meta_data ->> 'name'),
    new.raw_user_meta_data ->> 'avatar_url',
    coalesce(new.app_metadata ->> 'provider', 'unknown')
  )
  on conflict (id) do nothing;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
after insert on auth.users
for each row execute procedure public.handle_new_user();
