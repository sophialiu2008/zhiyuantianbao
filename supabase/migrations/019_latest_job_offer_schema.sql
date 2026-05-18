create table if not exists public.company_name_aliases (
  id bigserial primary key,
  raw_name text not null unique,
  standard_name text not null,
  verification_status text not null default '待核实' check (verification_status in ('高', '中', '待核实')),
  source_url text,
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.company_name_aliases enable row level security;

drop policy if exists "public read company name aliases" on public.company_name_aliases;
create policy "public read company name aliases"
on public.company_name_aliases for select
to anon, authenticated
using (true);

create table if not exists public.latest_job_offer_import_staging (
  id bigserial primary key,
  import_batch text not null,
  source_row_number int not null,
  offer_index int not null,
  video_filename text,
  school_name text,
  major_name text,
  degree_level text,
  data_year int,
  company_name_raw text,
  company_name_standard text,
  company_verification_status text not null default '待核实',
  monthly_salary int,
  annual_bonus int,
  first_year_income int,
  work_content text,
  employment_city text,
  salary_verification_status text not null default 'pending',
  credibility text not null default '中',
  verification_status text not null default 'reviewed',
  issue_codes text[] not null default '{}'::text[],
  extraction_notes text,
  raw_payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique (import_batch, source_row_number, offer_index)
);

create index if not exists idx_latest_job_offer_import_batch
  on public.latest_job_offer_import_staging (import_batch, source_row_number, offer_index);

alter table public.latest_job_offer_import_staging enable row level security;
drop policy if exists "public read latest job offer import staging" on public.latest_job_offer_import_staging;

alter table public.job_data
  add column if not exists offer_index int,
  add column if not exists company_name_raw text,
  add column if not exists company_name_standard text,
  add column if not exists company_verification_status text not null default '待核实',
  add column if not exists salary_verification_status text not null default 'pending',
  add column if not exists video_filename text,
  add column if not exists extraction_notes text;

alter table public.job_data drop constraint if exists job_data_company_verification_status_check;
alter table public.job_data
  add constraint job_data_company_verification_status_check
  check (company_verification_status in ('高', '中', '待核实'));

alter table public.job_data drop constraint if exists job_data_salary_verification_status_check;
alter table public.job_data
  add constraint job_data_salary_verification_status_check
  check (salary_verification_status in ('verified', 'reviewed', 'pending'));

create index if not exists idx_job_data_offer_company
  on public.job_data (company_name_standard, company_verification_status);

create index if not exists idx_job_data_offer_row
  on public.job_data (school_name, major_name, data_year desc, offer_index);

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
  'latest_job_excel_offer_2026',
  '最新就业资料.xlsx',
  '视频转写/OCR整理就业offer',
  2026,
  '中',
  '按批次更新',
  '每行最多拆分4个offer，语音转写和画面字幕OCR仅用于离线校验，不作为正式字段入库'
)
on conflict (source_key) do update set
  source_name = excluded.source_name,
  source_type = excluded.source_type,
  source_year = excluded.source_year,
  credibility = excluded.credibility,
  update_frequency = excluded.update_frequency,
  notes = excluded.notes;
