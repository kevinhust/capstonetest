-- Health Butler schema bootstrap
-- Safe to run multiple times

create extension if not exists pgcrypto;

create table if not exists public.profiles (
  id text primary key,
  full_name text,
  age integer,
  gender text,
  height_cm numeric,
  weight_kg numeric,
  goal text,
  restrictions text,
  activity text,
  diet text,
  preferences_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.daily_logs (
  id uuid primary key default gen_random_uuid(),
  user_id text not null references public.profiles(id) on delete cascade,
  date date not null,
  calories_intake numeric default 0,
  protein_g numeric default 0,
  steps_count integer default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (user_id, date)
);

create table if not exists public.chat_messages (
  id uuid primary key default gen_random_uuid(),
  user_id text not null references public.profiles(id) on delete cascade,
  role text not null,
  content text not null,
  created_at timestamptz not null default now()
);

create table if not exists public.meals (
  id uuid primary key default gen_random_uuid(),
  user_id text not null references public.profiles(id) on delete cascade,
  dish_name text not null,
  calories numeric default 0,
  protein_g numeric default 0,
  carbs_g numeric default 0,
  fat_g numeric default 0,
  confidence_score numeric default 0,
  created_at timestamptz not null default now()
);

create table if not exists public.workout_logs (
  id uuid primary key default gen_random_uuid(),
  user_id text not null references public.profiles(id) on delete cascade,
  exercise_name text not null,
  duration_min integer not null default 0,
  kcal_estimate numeric not null default 0,
  status text not null default 'recommended',
  source text not null default 'fitness_agent',
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists public.workout_routines (
  id uuid primary key default gen_random_uuid(),
  user_id text not null references public.profiles(id) on delete cascade,
  exercise_name text not null,
  target_per_week integer not null default 3,
  status text not null default 'active',
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_daily_logs_user_date on public.daily_logs (user_id, date desc);
create index if not exists idx_chat_messages_user_created on public.chat_messages (user_id, created_at desc);
create index if not exists idx_meals_user_created on public.meals (user_id, created_at desc);
create index if not exists idx_workout_logs_user_created on public.workout_logs (user_id, created_at desc);
create index if not exists idx_workout_routines_user_status on public.workout_routines (user_id, status);

-- Backfill foreign-key relationships for existing deployments that were created
-- before table-level REFERENCES were added.
do $$
begin
  if not exists (
    select 1
    from information_schema.columns
    where table_schema = 'public'
      and table_name = 'profiles'
      and column_name = 'preferences_json'
  ) then
    alter table public.profiles
      add column preferences_json jsonb not null default '{}'::jsonb;
  end if;
end
$$;

do $$
begin
  if not exists (
    select 1 from pg_constraint where conname = 'daily_logs_user_id_fkey'
  ) then
    alter table public.daily_logs
      add constraint daily_logs_user_id_fkey
      foreign key (user_id) references public.profiles(id) on delete cascade not valid;
  end if;
end
$$;

do $$
begin
  if not exists (
    select 1 from pg_constraint where conname = 'chat_messages_user_id_fkey'
  ) then
    alter table public.chat_messages
      add constraint chat_messages_user_id_fkey
      foreign key (user_id) references public.profiles(id) on delete cascade not valid;
  end if;
end
$$;

do $$
begin
  if not exists (
    select 1 from pg_constraint where conname = 'meals_user_id_fkey'
  ) then
    alter table public.meals
      add constraint meals_user_id_fkey
      foreign key (user_id) references public.profiles(id) on delete cascade not valid;
  end if;
end
$$;

do $$
begin
  if not exists (
    select 1 from pg_constraint where conname = 'workout_logs_user_id_fkey'
  ) then
    alter table public.workout_logs
      add constraint workout_logs_user_id_fkey
      foreign key (user_id) references public.profiles(id) on delete cascade not valid;
  end if;
end
$$;

do $$
begin
  if not exists (
    select 1 from pg_constraint where conname = 'workout_routines_user_id_fkey'
  ) then
    alter table public.workout_routines
      add constraint workout_routines_user_id_fkey
      foreign key (user_id) references public.profiles(id) on delete cascade not valid;
  end if;
end
$$;
