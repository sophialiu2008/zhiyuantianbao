create table if not exists public.data_sources (
  id bigserial primary key,
  source_key text not null unique,
  source_name text not null,
  source_type text not null,
  source_year int,
  source_url text,
  credibility text not null default '参考' check (credibility in ('高', '中', '参考', '待核实')),
  update_frequency text,
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.school_profiles (
  school_code text primary key,
  school_name text not null,
  school_name_normalized text not null,
  school_tags text[] not null default '{}'::text[],
  province text,
  city text,
  campus_city text,
  city_tier text,
  school_type text,
  ownership text,
  is_985 boolean not null default false,
  is_211 boolean not null default false,
  is_double_first_class boolean not null default false,
  double_first_class_subjects text[] not null default '{}'::text[],
  has_postgrad_recommend boolean,
  postgrad_recommend_rate numeric(5,2),
  postgrad_destinations text[] not null default '{}'::text[],
  profile_source_id bigint references public.data_sources(id),
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.school_profiles
  drop constraint if exists school_profiles_school_name_normalized_key;

create table if not exists public.school_rankings (
  id bigserial primary key,
  school_code text references public.school_profiles(school_code) on delete cascade,
  school_name text not null,
  ranking_name text not null default '软科中国大学排名',
  ranking_year int not null,
  rank_no int,
  rank_label text,
  source_id bigint references public.data_sources(id),
  created_at timestamptz not null default now(),
  unique (school_code, ranking_name, ranking_year)
);

create table if not exists public.discipline_evaluations (
  id bigserial primary key,
  school_code text references public.school_profiles(school_code) on delete cascade,
  school_name text not null,
  discipline_name text not null,
  evaluation_round text not null default '第四轮',
  evaluation_grade text not null,
  source_id bigint references public.data_sources(id),
  created_at timestamptz not null default now(),
  unique (school_code, discipline_name, evaluation_round)
);

create table if not exists public.major_profiles (
  major_code text primary key,
  major_name text not null unique,
  discipline_category text,
  major_category text,
  degree_type text,
  standard_duration text,
  subject_requirement text,
  industry_outlook text,
  description text,
  job_directions text[] not null default '{}'::text[],
  typical_employers text[] not null default '{}'::text[],
  further_study_directions text[] not null default '{}'::text[],
  source_id bigint references public.data_sources(id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.school_major_profiles (
  id bigserial primary key,
  school_code text references public.school_profiles(school_code) on delete cascade,
  major_code text references public.major_profiles(major_code) on delete cascade,
  school_name text not null,
  major_name text not null,
  subject_requirement text,
  discipline_grade text,
  notes text,
  source_id bigint references public.data_sources(id),
  created_at timestamptz not null default now(),
  unique (school_code, major_code)
);

create table if not exists public.job_data (
  id bigserial primary key,
  school_code text references public.school_profiles(school_code) on delete set null,
  school_name text not null,
  major_code text references public.major_profiles(major_code) on delete set null,
  major_name text not null,
  degree_level text not null default '本科',
  job_directions text[] not null default '{}'::text[],
  employers text[] not null default '{}'::text[],
  employer_tiers text[] not null default '{}'::text[],
  monthly_salary_min int,
  monthly_salary_max int,
  annual_bonus_min int,
  annual_bonus_max int,
  first_year_income_min int,
  first_year_income_max int,
  employment_city text,
  data_year int,
  source_url text,
  source_id bigint references public.data_sources(id),
  credibility text not null default '待核实' check (credibility in ('高', '中', '待核实')),
  verification_status text not null default 'pending' check (verification_status in ('verified', 'reviewed', 'pending')),
  notes text,
  created_at timestamptz not null default now()
);

create index if not exists idx_school_profiles_name_trgm
  on public.school_profiles using gin (school_name_normalized gin_trgm_ops);
create index if not exists idx_major_profiles_name_trgm
  on public.major_profiles using gin (major_name gin_trgm_ops);
create index if not exists idx_job_data_school_major
  on public.job_data (school_name, major_name, data_year desc);
create index if not exists idx_job_data_credibility
  on public.job_data (credibility, verification_status);

alter table public.data_sources enable row level security;
alter table public.school_profiles enable row level security;
alter table public.school_rankings enable row level security;
alter table public.discipline_evaluations enable row level security;
alter table public.major_profiles enable row level security;
alter table public.school_major_profiles enable row level security;
alter table public.job_data enable row level security;

drop policy if exists "public read data sources" on public.data_sources;
create policy "public read data sources" on public.data_sources for select to anon, authenticated using (true);
drop policy if exists "public read school profiles" on public.school_profiles;
create policy "public read school profiles" on public.school_profiles for select to anon, authenticated using (true);
drop policy if exists "public read school rankings" on public.school_rankings;
create policy "public read school rankings" on public.school_rankings for select to anon, authenticated using (true);
drop policy if exists "public read discipline evaluations" on public.discipline_evaluations;
create policy "public read discipline evaluations" on public.discipline_evaluations for select to anon, authenticated using (true);
drop policy if exists "public read major profiles" on public.major_profiles;
create policy "public read major profiles" on public.major_profiles for select to anon, authenticated using (true);
drop policy if exists "public read school major profiles" on public.school_major_profiles;
create policy "public read school major profiles" on public.school_major_profiles for select to anon, authenticated using (true);
drop policy if exists "public read verified job data" on public.job_data;
create policy "public read verified job data"
on public.job_data for select
to anon, authenticated
using (credibility in ('高', '中') and verification_status in ('verified', 'reviewed'));

insert into public.data_sources (source_key, source_name, source_type, source_year, credibility, update_frequency, notes)
values
  ('hebei_rank_table', '河北省一分一档表', '官方数据', 2025, '高', '每年6-7月', '用于分数换算位次'),
  ('hebei_admission_records', '河北省本科批平行志愿投档统计表', '官方数据', 2025, '高', '每年7-8月', '用于录取位次趋势和推荐'),
  ('school_profile_manual', '院校基础画像人工维护表', '人工整理', 2025, '中', '按需更新', '用于补充层次、类型、办学性质、保研等字段'),
  ('major_profile_manual', '专业基础画像人工维护表', '人工整理', 2025, '中', '按需更新', '用于补充专业描述、方向、学制、选科等字段'),
  ('job_offer_manual', '就业offer人工整理表', '社媒/公开资料整理', 2025, '参考', '持续更新', '用于展示就业方向和薪资样本')
on conflict (source_key) do update set
  source_name = excluded.source_name,
  source_type = excluded.source_type,
  source_year = excluded.source_year,
  credibility = excluded.credibility,
  update_frequency = excluded.update_frequency,
  notes = excluded.notes,
  updated_at = now();

insert into public.school_profiles (
  school_code,
  school_name,
  school_name_normalized,
  school_tags,
  province,
  city,
  campus_city,
  profile_source_id
)
select
  a.school_code,
  (array_agg(a.school_name order by a.year desc))[1] as school_name,
  public.normalize_school_name((array_agg(a.school_name order by a.year desc))[1]) as school_name_normalized,
  coalesce(
    (
      select array_agg(distinct tag_item.tag order by tag_item.tag)
      from public.admission_records aa
      cross join lateral unnest(aa.school_tags) as tag_item(tag)
      where aa.school_code = a.school_code
    ),
    '{}'::text[]
  ) as school_tags,
  (array_agg(loc.province order by a.year desc))[1] as province,
  (array_agg(loc.city order by a.year desc))[1] as city,
  (array_agg(loc.campus_city order by a.year desc))[1] as campus_city,
  (select id from public.data_sources where source_key = 'hebei_admission_records')
from public.admission_records a
left join public.school_locations loc
  on loc.school_name_normalized = public.normalize_school_name(a.school_name)
where a.school_code is not null and a.school_code <> ''
group by a.school_code
on conflict (school_code) do update set
  school_name = excluded.school_name,
  school_name_normalized = excluded.school_name_normalized,
  school_tags = excluded.school_tags,
  province = coalesce(public.school_profiles.province, excluded.province),
  city = coalesce(public.school_profiles.city, excluded.city),
  campus_city = coalesce(public.school_profiles.campus_city, excluded.campus_city),
  updated_at = now();

insert into public.major_profiles (
  major_code,
  major_name,
  description,
  source_id
)
select
  'major_' || md5(a.major_name) as major_code,
  a.major_name,
  '该专业已在河北近年投档数据中出现，详细培养方向、就业去向和薪资样本待持续补充。' as description,
  (select id from public.data_sources where source_key = 'hebei_admission_records')
from public.admission_records a
where a.major_name is not null and a.major_name <> ''
group by a.major_name
on conflict (major_code) do update set
  major_name = excluded.major_name,
  updated_at = now();

insert into public.school_major_profiles (
  school_code,
  major_code,
  school_name,
  major_name,
  source_id
)
select
  a.school_code,
  'major_' || md5(a.major_name),
  (array_agg(a.school_name order by a.year desc))[1],
  (array_agg(a.major_name order by a.year desc))[1],
  (select id from public.data_sources where source_key = 'hebei_admission_records')
from public.admission_records a
where a.school_code is not null and a.school_code <> ''
  and a.major_name is not null and a.major_name <> ''
group by a.school_code, a.major_name
on conflict (school_code, major_code) do update set
  school_name = excluded.school_name,
  major_name = excluded.major_name;

create or replace function public.get_school_detail(
  p_school_query text,
  p_subject text default 'physics'
)
returns jsonb
language sql
stable
security definer
set search_path = public
as $$
  with q as (
    select
      trim(coalesce(p_school_query, '')) as raw_query,
      public.normalize_school_name(trim(coalesce(p_school_query, ''))) as normalized_query
  ),
  school as (
    select sp.*
    from public.school_profiles sp, q
    where q.raw_query <> ''
      and (
        sp.school_name_normalized = q.normalized_query
        or sp.school_name_normalized ilike '%' || q.normalized_query || '%'
        or sp.school_name ilike '%' || q.raw_query || '%'
      )
    order by similarity(sp.school_name_normalized, q.normalized_query) desc nulls last, sp.school_name
    limit 1
  ),
  admission_summary as (
    select
      a.year,
      min(a.min_score) filter (where a.min_score is not null) as min_score,
      min(a.min_rank) filter (where a.min_rank is not null) as best_rank,
      max(a.min_rank) filter (where a.min_rank is not null) as worst_rank,
      count(*) as major_count
    from public.admission_records a
    join school s on a.school_code = s.school_code
    where a.subject = p_subject
    group by a.year
    order by a.year desc
  )
  select coalesce(
    jsonb_build_object(
      'profile', to_jsonb(s),
      'rankings', coalesce((select jsonb_agg(to_jsonb(r) order by r.ranking_year desc) from public.school_rankings r where r.school_code = s.school_code), '[]'::jsonb),
      'disciplines', coalesce((select jsonb_agg(to_jsonb(d) order by d.evaluation_grade, d.discipline_name) from public.discipline_evaluations d where d.school_code = s.school_code), '[]'::jsonb),
      'admissionTrend', coalesce((select jsonb_agg(to_jsonb(a) order by a.year desc) from admission_summary a), '[]'::jsonb),
      'jobCoverage', coalesce((select count(distinct jd.major_name) from public.job_data jd where jd.school_code = s.school_code and jd.credibility in ('高','中') and jd.verification_status in ('verified','reviewed')), 0)
    ),
    '{}'::jsonb
  )
  from school s;
$$;

create or replace function public.get_major_detail(
  p_major_query text,
  p_school_query text default '',
  p_subject text default 'physics'
)
returns jsonb
language sql
stable
security definer
set search_path = public
as $$
  with q as (
    select
      trim(coalesce(p_major_query, '')) as major_query,
      trim(coalesce(p_school_query, '')) as school_query,
      public.normalize_school_name(trim(coalesce(p_school_query, ''))) as normalized_school_query
  ),
  major_match as (
    select mp.*
    from public.major_profiles mp, q
    where q.major_query <> ''
      and (mp.major_name = q.major_query or mp.major_name ilike '%' || q.major_query || '%' or mp.major_code = q.major_query)
    order by similarity(mp.major_name, q.major_query) desc nulls last, mp.major_name
    limit 1
  ),
  school_match as (
    select sp.*
    from public.school_profiles sp, q
    where q.school_query <> ''
      and (
        sp.school_name_normalized = q.normalized_school_query
        or sp.school_name_normalized ilike '%' || q.normalized_school_query || '%'
        or sp.school_name ilike '%' || q.school_query || '%'
      )
    order by similarity(sp.school_name_normalized, q.normalized_school_query) desc nulls last
    limit 1
  ),
  school_major as (
    select smp.*
    from public.school_major_profiles smp
    join major_match mm on smp.major_code = mm.major_code
    left join school_match sm on smp.school_code = sm.school_code
    where (select school_query from q) = '' or sm.school_code is not null
    limit 1
  ),
  admission_compare as (
    select
      a.school_code,
      (array_agg(a.school_name order by a.year desc))[1] as school_name,
      a.major_name,
      min(a.min_rank) filter (where a.min_rank is not null) as best_rank,
      max(a.min_rank) filter (where a.min_rank is not null) as worst_rank,
      count(distinct a.year)::int as history_years
    from public.admission_records a
    join major_match mm on a.major_name = mm.major_name or a.major_code = mm.major_code
    where a.subject = p_subject and a.min_rank is not null
    group by a.school_code, a.major_name
    order by best_rank asc
    limit 20
  )
  select coalesce(
    jsonb_build_object(
      'profile', to_jsonb(mm),
      'schoolMajor', coalesce((select to_jsonb(smp) from school_major smp), '{}'::jsonb),
      'jobs', coalesce((
        select jsonb_agg(to_jsonb(jd) order by jd.data_year desc nulls last, jd.first_year_income_min desc nulls last)
        from public.job_data jd
        where (jd.major_code = mm.major_code or jd.major_name = mm.major_name)
          and ((select school_query from q) = '' or jd.school_code = (select sm.school_code from school_match sm))
          and jd.credibility in ('高','中')
          and jd.verification_status in ('verified','reviewed')
      ), '[]'::jsonb),
      'schoolCompare', coalesce((select jsonb_agg(to_jsonb(ac) order by ac.best_rank asc) from admission_compare ac), '[]'::jsonb)
    ),
    '{}'::jsonb
  )
  from major_match mm;
$$;

create or replace function public.get_jobs_overview()
returns jsonb
language sql
stable
security definer
set search_path = public
as $$
  select jsonb_build_object(
    'schoolCount', count(distinct jd_outer.school_name),
    'majorCount', count(distinct jd_outer.major_name),
    'recordCount', count(*),
    'byCategory', coalesce((
      select jsonb_agg(row_to_json(x) order by x.record_count desc)
      from (
        select coalesce(mp.discipline_category, '未分类') as category, count(*) as record_count
        from public.job_data jd
        left join public.major_profiles mp on jd.major_code = mp.major_code or jd.major_name = mp.major_name
        where jd.credibility in ('高','中') and jd.verification_status in ('verified','reviewed')
        group by coalesce(mp.discipline_category, '未分类')
      ) x
    ), '[]'::jsonb),
    'latestRecords', coalesce((
      select jsonb_agg(to_jsonb(j) order by j.created_at desc)
      from (
        select *
        from public.job_data
        where credibility in ('高','中') and verification_status in ('verified','reviewed')
        order by created_at desc
        limit 20
      ) j
    ), '[]'::jsonb)
  )
  from public.job_data jd_outer
  where jd_outer.credibility in ('高','中') and jd_outer.verification_status in ('verified','reviewed');
$$;
