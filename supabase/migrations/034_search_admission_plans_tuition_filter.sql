drop function if exists public.search_admission_plans(
  int, text, text, text, text, text, text, text, text[], text, boolean, int, int
);

create or replace function public.search_admission_plans(
  p_plan_year int default 2026,
  p_subject text default 'physics',
  p_batch text default '',
  p_plan_nature text default '',
  p_volunteer_mode text default '',
  p_query text default '',
  p_school_query text default '',
  p_major_query text default '',
  p_subject_requirements text[] default '{}',
  p_school_tag text default '',
  p_high_level_sports boolean default false,
  p_tuition_min int default null,
  p_tuition_max int default null,
  p_tuition_unknown boolean default false,
  p_limit int default 50,
  p_offset int default 0
)
returns table (
  id bigint,
  year int,
  subject text,
  batch text,
  plan_nature text,
  volunteer_mode text,
  school_code text,
  school_name text,
  school_tags text[],
  major_code text,
  major_name text,
  major_remark text,
  qualification_type text,
  subject_requirement text,
  plan_count int,
  duration_years int,
  tuition int,
  source_page int,
  source_row int,
  total_count bigint
)
language sql
stable
security definer
set search_path = public
as $$
  with filtered as (
    select p.*
    from public.admission_plans p
    where p.year = p_plan_year
      and p.subject = p_subject
      and (coalesce(nullif(trim(p_batch), ''), '') = '' or p.batch = trim(p_batch))
      and (coalesce(nullif(trim(p_plan_nature), ''), '') = '' or p.plan_nature = trim(p_plan_nature))
      and (coalesce(nullif(trim(p_volunteer_mode), ''), '') = '' or p.volunteer_mode = trim(p_volunteer_mode))
      and (
        coalesce(cardinality(p_subject_requirements), 0) = 0
        or coalesce(nullif(p.subject_requirement, ''), '不限') = any(p_subject_requirements)
      )
      and (coalesce(nullif(trim(p_school_tag), ''), '') = '' or trim(p_school_tag) = any(p.school_tags))
      and (
        not p_high_level_sports
        or p.major_remark ilike '%高水平%'
        or (p.batch = '本科提前批C段' and coalesce(p.plan_count, 0) = 0)
      )
      and (
        not p_tuition_unknown
        or p.tuition is null
        or p.tuition <= 0
      )
      and (
        p_tuition_unknown
        or (p_tuition_min is null and p_tuition_max is null)
        or (
          p.tuition is not null
          and p.tuition > 0
          and (p_tuition_min is null or p.tuition >= p_tuition_min)
          and (p_tuition_max is null or p.tuition <= p_tuition_max)
        )
      )
      and (
        coalesce(nullif(trim(p_query), ''), '') = ''
        or p.school_name ilike '%' || trim(p_query) || '%'
        or p.major_name ilike '%' || trim(p_query) || '%'
        or p.school_code ilike '%' || trim(p_query) || '%'
        or p.major_code ilike '%' || trim(p_query) || '%'
        or p.major_remark ilike '%' || trim(p_query) || '%'
      )
      and (
        coalesce(nullif(trim(p_school_query), ''), '') = ''
        or p.school_name ilike '%' || trim(p_school_query) || '%'
        or p.school_code ilike '%' || trim(p_school_query) || '%'
      )
      and (
        coalesce(nullif(trim(p_major_query), ''), '') = ''
        or p.major_name ilike '%' || trim(p_major_query) || '%'
        or p.major_code ilike '%' || trim(p_major_query) || '%'
      )
  )
  select
    f.id,
    f.year,
    f.subject,
    f.batch,
    f.plan_nature,
    f.volunteer_mode,
    f.school_code,
    f.school_name,
    f.school_tags,
    f.major_code,
    f.major_name,
    f.major_remark,
    case
      when f.major_remark ilike '%高水平%' or (f.batch = '本科提前批C段' and coalesce(f.plan_count, 0) = 0) then '高水平运动队'
      when f.major_remark ilike '%公安%' then '公安类'
      when f.major_remark ilike '%航海%' then '航海类'
      else ''
    end as qualification_type,
    f.subject_requirement,
    f.plan_count,
    f.duration_years,
    f.tuition,
    f.source_page,
    f.source_row,
    count(*) over() as total_count
  from filtered f
  order by
    case f.batch
      when '本科提前批A段' then 1
      when '本科提前批B段' then 2
      when '本科提前批C段' then 3
      when '本科批' then 4
      when '专科提前批' then 5
      when '专科批' then 6
      else 99
    end,
    f.school_code,
    f.source_page nulls last,
    f.source_row nulls last,
    f.major_code
  limit greatest(1, least(p_limit, 100))
  offset greatest(0, p_offset);
$$;

notify pgrst, 'reload schema';
