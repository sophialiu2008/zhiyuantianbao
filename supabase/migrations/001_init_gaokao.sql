create extension if not exists pg_trgm;

create table if not exists public.rank_table (
  id bigserial primary key,
  year int not null,
  subject text not null check (subject in ('physics', 'history')),
  score int not null,
  count_at_score int not null,
  cumulative_rank int not null,
  score_label text not null,
  source_file text not null,
  source_row int not null,
  created_at timestamptz not null default now(),
  unique (year, subject, score)
);

create table if not exists public.admission_records (
  id bigserial primary key,
  year int not null,
  subject text not null check (subject in ('physics', 'history')),
  admission_type text not null default '非定向',
  school_code text not null,
  school_name text not null,
  school_name_raw text not null,
  school_tags text[] not null default '{}',
  major_code text not null,
  major_name text not null,
  min_score int,
  min_rank int,
  chinese_math_score int,
  chinese_math_highest int,
  foreign_language_score int,
  first_choice_subject_score int,
  second_choice_subject_highest int,
  second_choice_subject_second int,
  volunteer_no int,
  remark text not null default '',
  source_file text not null,
  source_row int not null,
  created_at timestamptz not null default now(),
  unique (year, subject, admission_type, school_code, major_code, major_name)
);

create table if not exists public.data_import_batches (
  id bigserial primary key,
  source text not null,
  imported_at timestamptz not null default now(),
  rank_count int not null default 0,
  admission_count int not null default 0,
  notes text
);

create table if not exists public.volunteer_lists (
  id uuid primary key default gen_random_uuid(),
  device_id text not null,
  title text not null default '我的志愿表',
  items jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_rank_table_lookup
  on public.rank_table (year, subject, score);

create index if not exists idx_admission_year_subject_rank
  on public.admission_records (year, subject, min_rank);

create index if not exists idx_admission_school_major_history
  on public.admission_records (subject, school_name, major_name, year);

create index if not exists idx_admission_school_trgm
  on public.admission_records using gin (school_name gin_trgm_ops);

create index if not exists idx_admission_major_trgm
  on public.admission_records using gin (major_name gin_trgm_ops);

create index if not exists idx_admission_tags
  on public.admission_records using gin (school_tags);

create index if not exists idx_volunteer_lists_device
  on public.volunteer_lists (device_id, updated_at desc);

alter table public.rank_table enable row level security;
alter table public.admission_records enable row level security;
alter table public.data_import_batches enable row level security;
alter table public.volunteer_lists enable row level security;

drop policy if exists "public read rank table" on public.rank_table;
create policy "public read rank table"
on public.rank_table for select
to anon, authenticated
using (true);

drop policy if exists "public read admission records" on public.admission_records;
create policy "public read admission records"
on public.admission_records for select
to anon, authenticated
using (true);

drop policy if exists "public read import batches" on public.data_import_batches;
create policy "public read import batches"
on public.data_import_batches for select
to anon, authenticated
using (true);

drop policy if exists "device read own volunteer lists" on public.volunteer_lists;
create policy "device read own volunteer lists"
on public.volunteer_lists for select
to anon, authenticated
using (true);

drop policy if exists "device insert volunteer lists" on public.volunteer_lists;
create policy "device insert volunteer lists"
on public.volunteer_lists for insert
to anon, authenticated
with check (true);

drop policy if exists "device update volunteer lists" on public.volunteer_lists;
create policy "device update volunteer lists"
on public.volunteer_lists for update
to anon, authenticated
using (true)
with check (true);

create or replace function public.get_rank_record(
  p_year int,
  p_subject text,
  p_score int
)
returns table (
  year int,
  subject text,
  score int,
  count_at_score int,
  cumulative_rank int,
  score_label text
)
language sql
stable
security definer
set search_path = public
as $$
  select r.year, r.subject, r.score, r.count_at_score, r.cumulative_rank, r.score_label
  from public.rank_table r
  where r.year = p_year
    and r.subject = p_subject
    and r.score <= p_score
  order by r.score desc
  limit 1;
$$;

create or replace function public.recommend_admissions(
  p_year int,
  p_subject text,
  p_user_rank int,
  p_query text default '',
  p_risk text default 'all',
  p_tag text default 'all',
  p_limit int default 50,
  p_offset int default 0
)
returns table (
  id bigint,
  year int,
  subject text,
  school_code text,
  school_name text,
  school_tags text[],
  major_code text,
  major_name text,
  min_score int,
  min_rank int,
  admission_type text,
  remark text,
  history_years int,
  best_rank int,
  worst_rank int,
  avg_rank int,
  basis_rank int,
  rank_diff int,
  risk_type text,
  total_count bigint
)
language sql
stable
security definer
set search_path = public
as $$
  with current_rows as (
    select a.*
    from public.admission_records a
    where a.year = p_year
      and a.subject = p_subject
      and a.min_score is not null
      and a.min_rank is not null
      and (
        coalesce(nullif(trim(p_query), ''), '') = ''
        or a.school_name ilike '%' || trim(p_query) || '%'
        or a.major_name ilike '%' || trim(p_query) || '%'
        or a.school_code ilike '%' || trim(p_query) || '%'
        or a.major_code ilike '%' || trim(p_query) || '%'
      )
      and (
        p_tag = 'all'
        or p_tag = any(a.school_tags)
        or a.major_name ilike '%' || p_tag || '%'
      )
  ),
  scored as (
    select
      c.*,
      h.history_years,
      h.best_rank,
      h.worst_rank,
      h.avg_rank,
      h.worst_rank as basis_rank,
      (h.worst_rank - p_user_rank) as rank_diff,
      case
        when h.history_years = 0 then 'unknown'
        when ((h.worst_rank - p_user_rank)::numeric / greatest(p_user_rank, 1)) < -0.15 then 'unknown'
        when ((h.worst_rank - p_user_rank)::numeric / greatest(p_user_rank, 1)) < -0.03 then 'reach'
        when ((h.worst_rank - p_user_rank)::numeric / greatest(p_user_rank, 1)) <= 0.12 then 'match'
        else 'safe'
      end as risk_type
    from current_rows c
    cross join lateral (
      select
        count(*)::int as history_years,
        max(hh.min_rank)::int as best_rank,
        min(hh.min_rank)::int as worst_rank,
        round(avg(hh.min_rank))::int as avg_rank
      from public.admission_records hh
      where hh.subject = c.subject
        and hh.school_name = c.school_name
        and hh.major_name = c.major_name
        and hh.min_rank is not null
    ) h
  ),
  filtered as (
    select *
    from scored
    where risk_type <> 'unknown'
      and (p_risk = 'all' or risk_type = p_risk)
  )
  select
    f.id,
    f.year,
    f.subject,
    f.school_code,
    f.school_name,
    f.school_tags,
    f.major_code,
    f.major_name,
    f.min_score,
    f.min_rank,
    f.admission_type,
    f.remark,
    f.history_years,
    f.best_rank,
    f.worst_rank,
    f.avg_rank,
    f.basis_rank,
    f.rank_diff,
    f.risk_type,
    count(*) over() as total_count
  from filtered f
  order by
    case f.risk_type when 'match' then 1 when 'safe' then 2 when 'reach' then 3 else 4 end,
    abs(f.rank_diff),
    f.min_rank
  limit greatest(1, least(p_limit, 100))
  offset greatest(0, p_offset);
$$;
