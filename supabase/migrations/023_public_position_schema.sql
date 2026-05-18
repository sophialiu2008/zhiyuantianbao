create table if not exists public.civil_service_positions (
  id bigserial primary key,
  position_code text not null unique,
  exam_area text,
  department text,
  unit_name text,
  position_name text,
  recruit_count int,
  education_min text,
  degree_min text,
  major_requirement text,
  other_requirement text,
  essay_type text,
  source_year int not null default 2026,
  raw_payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists public.military_civilian_positions (
  id bigserial primary key,
  position_code text not null unique,
  employer_no text,
  employer_name text,
  position_category text,
  position_name text,
  work_content text,
  recruit_count int,
  shortlist_ratio text,
  source_category text,
  education text,
  degree text,
  major_requirement text,
  exam_subject text,
  title_graduate text,
  title_social text,
  qualification_graduate text,
  qualification_social text,
  other_requirement text,
  work_location text,
  contact_phone text,
  source_year int not null default 2026,
  raw_payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists public.public_position_matches (
  id bigserial primary key,
  major_code text,
  major_name text not null,
  major_name_normalized text not null,
  position_source text not null check (position_source in ('civil_service', 'military_civilian')),
  position_code text not null,
  match_level text not null check (match_level in ('high', 'medium', 'low')),
  match_type text not null,
  match_reason text not null,
  created_at timestamptz not null default now(),
  unique (major_name_normalized, position_source, position_code, match_type)
);

create index if not exists idx_civil_service_positions_major_req
  on public.civil_service_positions using gin (major_requirement gin_trgm_ops);

create index if not exists idx_military_civilian_positions_major_req
  on public.military_civilian_positions using gin (major_requirement gin_trgm_ops);

create index if not exists idx_public_position_matches_major
  on public.public_position_matches (major_name_normalized, match_level, position_source);

create index if not exists idx_public_position_matches_position
  on public.public_position_matches (position_source, position_code);

alter table public.civil_service_positions enable row level security;
alter table public.military_civilian_positions enable row level security;
alter table public.public_position_matches enable row level security;

drop policy if exists "public read civil service positions" on public.civil_service_positions;
create policy "public read civil service positions"
on public.civil_service_positions for select
to anon, authenticated
using (true);

drop policy if exists "public read military civilian positions" on public.military_civilian_positions;
create policy "public read military civilian positions"
on public.military_civilian_positions for select
to anon, authenticated
using (true);

drop policy if exists "public read public position matches" on public.public_position_matches;
create policy "public read public position matches"
on public.public_position_matches for select
to anon, authenticated
using (true);

create or replace function public.normalize_major_name(p_name text)
returns text
language sql
immutable
as $$
  select regexp_replace(
    regexp_replace(coalesce(p_name, ''), '[（(].*?[）)]', '', 'g'),
    '\s+',
    '',
    'g'
  );
$$;

create or replace function public.search_public_positions_by_major(
  p_major_query text,
  p_include_low boolean default false,
  p_limit int default 80
)
returns jsonb
language sql
stable
security definer
set search_path = public
as $$
  with q as (
    select public.normalize_major_name(trim(coalesce(p_major_query, ''))) as major_name_normalized
  ),
  matched as (
    select m.*
    from public.public_position_matches m, q
    where q.major_name_normalized <> ''
      and m.major_name_normalized = q.major_name_normalized
      and (p_include_low or m.match_level in ('high', 'medium'))
  ),
  civil_rows as (
    select
      m.match_level,
      m.match_type,
      m.match_reason,
      to_jsonb(p) as position
    from matched m
    join public.civil_service_positions p on p.position_code = m.position_code
    where m.position_source = 'civil_service'
    order by
      case m.match_level when 'high' then 1 when 'medium' then 2 else 3 end,
      p.exam_area,
      p.department,
      p.position_code
    limit greatest(1, least(coalesce(p_limit, 80), 300))
  ),
  military_rows as (
    select
      m.match_level,
      m.match_type,
      m.match_reason,
      to_jsonb(p) as position
    from matched m
    join public.military_civilian_positions p on p.position_code = m.position_code
    where m.position_source = 'military_civilian'
    order by
      case m.match_level when 'high' then 1 when 'medium' then 2 else 3 end,
      p.work_location,
      p.employer_name,
      p.position_code
    limit greatest(1, least(coalesce(p_limit, 80), 300))
  )
  select jsonb_build_object(
    'civilServiceTotal', (select count(*) from matched where position_source = 'civil_service'),
    'militaryCivilianTotal', (select count(*) from matched where position_source = 'military_civilian'),
    'civilService', coalesce((select jsonb_agg(to_jsonb(civil_rows)) from civil_rows), '[]'::jsonb),
    'militaryCivilian', coalesce((select jsonb_agg(to_jsonb(military_rows)) from military_rows), '[]'::jsonb)
  );
$$;
