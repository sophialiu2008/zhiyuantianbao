insert into public.job_data (
  school_code, school_name, major_code, major_name, degree_level, job_directions, employers, employer_tiers,
  monthly_salary_min, monthly_salary_max, annual_bonus_min, annual_bonus_max, first_year_income_min, first_year_income_max,
  employment_city, data_year, source_id, credibility, verification_status, notes, offer_index, company_name_raw,
  company_name_standard, company_verification_status, salary_verification_status, video_filename, extraction_notes
)
select
  sp.school_code,
  s.school_name,
  mp.major_code,
  s.major_name,
  s.degree_level,
  case when s.work_content is null then '{}'::text[] else array[s.work_content]::text[] end,
  case when s.company_name_standard is null then '{}'::text[] else array[s.company_name_standard]::text[] end,
  '{}'::text[],
  s.monthly_salary,
  s.monthly_salary,
  s.annual_bonus,
  s.annual_bonus,
  s.first_year_income,
  s.first_year_income,
  s.employment_city,
  s.data_year,
  (select id from public.data_sources where source_key = 'jiuye_feijige_offer_extract_2026'),
  s.credibility,
  s.verification_status,
  'Excel row ' || s.source_row_number || ', offer ' || s.offer_index || case when cardinality(s.issue_codes) > 0 then ': ' || array_to_string(s.issue_codes, ',') else '' end,
  s.offer_index,
  s.company_name_raw,
  s.company_name_standard,
  s.company_verification_status,
  s.salary_verification_status,
  s.video_filename,
  s.extraction_notes
from public.latest_job_offer_import_staging s
left join lateral (
  select school_code from public.school_profiles
  where public.normalize_school_name(school_name) = public.normalize_school_name(s.school_name)
     or school_name = s.school_name
  order by case when school_name = s.school_name then 0 else 1 end, school_code
  limit 1
) sp on true
left join lateral (
  select major_code from public.major_profiles
  where major_name = s.major_name
  order by major_code
  limit 1
) mp on true
where s.import_batch = '就业飞机哥_2026_20260521'
  and s.school_name is not null
  and s.major_name is not null
  and s.company_name_raw is not null
  and not exists (
    select 1
    from public.job_data jd
    where public.normalize_school_name(jd.school_name) = public.normalize_school_name(s.school_name)
      and trim(jd.major_name) = trim(s.major_name)
  );

select
  count(*) filter (where source_id = (select id from public.data_sources where source_key = 'jiuye_feijige_offer_extract_2026')) as imported_this_source,
  count(distinct school_name || '|' || major_name) filter (where source_id = (select id from public.data_sources where source_key = 'jiuye_feijige_offer_extract_2026')) as imported_school_major_pairs,
  count(*) filter (where credibility in ('高', '中') and verification_status in ('verified', 'reviewed')) as visible_rows,
  count(*) as total_job_rows
from public.job_data;
