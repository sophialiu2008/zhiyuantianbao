create table if not exists public.job_data_import_staging (
  id bigserial primary key,
  import_batch text not null,
  source_row_number int not null,
  school_name text,
  major_name text,
  degree_level text,
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
  credibility text not null default '待核实',
  verification_status text not null default 'pending',
  issue_codes text[] not null default '{}'::text[],
  raw_payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique (import_batch, source_row_number)
);

create index if not exists idx_job_data_import_staging_batch
  on public.job_data_import_staging (import_batch, credibility, verification_status);

alter table public.job_data_import_staging enable row level security;

drop policy if exists "public read job data import staging" on public.job_data_import_staging;

update public.job_data
set credibility = '待核实'
where credibility not in ('高', '中', '待核实');

alter table public.job_data
  alter column degree_level set default '本科',
  alter column credibility set default '待核实';

alter table public.job_data drop constraint if exists job_data_credibility_check;
alter table public.job_data
  add constraint job_data_credibility_check
  check (credibility in ('高', '中', '待核实'));

drop policy if exists "public read verified job data" on public.job_data;
create policy "public read verified job data"
on public.job_data for select
to anon, authenticated
using (credibility in ('高', '中') and verification_status in ('verified', 'reviewed'));

insert into public.data_sources (
  source_key,
  source_name,
  source_type,
  source_year,
  credibility,
  update_frequency,
  notes
)
values (
  'job_excel_school_major_2026',
  '学校专业就业数据.xlsx',
  '人工整理就业样本',
  2026,
  '中',
  '按批次更新',
  '学校、专业、学历层次、岗位方向、典型企业、薪资区间、就业城市和毕业年份样本'
)
on conflict (source_key) do update set
  source_name = excluded.source_name,
  source_type = excluded.source_type,
  source_year = excluded.source_year,
  credibility = excluded.credibility,
  update_frequency = excluded.update_frequency,
  notes = excluded.notes;

create or replace function public.get_jobs_overview()
returns jsonb
language sql
stable
security definer
set search_path = public
as $$
  with visible_jobs as (
    select *
    from public.job_data
    where credibility in ('高', '中')
      and verification_status in ('verified', 'reviewed')
  )
  select jsonb_build_object(
    'schoolCount', coalesce((select count(distinct school_name) from visible_jobs), 0),
    'majorCount', coalesce((select count(distinct major_name) from visible_jobs), 0),
    'recordCount', coalesce((select count(*) from visible_jobs), 0),
    'byCategory', coalesce((
      select jsonb_agg(row_to_json(x) order by x.record_count desc)
      from (
        select coalesce(mp.discipline_category, '未分类') as category, count(*) as record_count
        from visible_jobs jd
        left join public.major_profiles mp
          on jd.major_code = mp.major_code
          or jd.major_name = mp.major_name
        group by coalesce(mp.discipline_category, '未分类')
      ) x
    ), '[]'::jsonb),
    'latestRecords', coalesce((
      select jsonb_agg(to_jsonb(j) order by j.created_at desc, j.id desc)
      from (
        select *
        from visible_jobs
        order by created_at desc, id desc
        limit 50
      ) j
    ), '[]'::jsonb)
  );
$$;
