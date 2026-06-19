create index if not exists idx_school_profiles_name_normalized
  on public.school_profiles (school_name_normalized);

create index if not exists idx_admission_records_norm_match
  on public.admission_records (
    subject,
    year,
    public.normalize_school_name(school_name),
    public.normalize_major_name(major_name)
  )
  where min_rank is not null;

create or replace function public.recommend_admission_plans(
  p_plan_year int default 2026,
  p_history_year int default 2025,
  p_subject text default 'physics',
  p_user_rank int default 0,
  p_query text default '',
  p_risk text default 'all',
  p_tag text default 'all',
  p_limit int default 50,
  p_offset int default 0,
  p_provinces text[] default '{}',
  p_cities text[] default '{}',
  p_batches text[] default '{}',
  p_subject_requirements text[] default '{}'
)
returns table (
  id bigint,
  year int,
  subject text,
  school_code text,
  school_name text,
  school_tags text[],
  province text,
  city text,
  campus_city text,
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
  history jsonb,
  total_count bigint,
  plan_id bigint,
  plan_year int,
  batch text,
  plan_nature text,
  volunteer_mode text,
  plan_count int,
  duration_years int,
  tuition int,
  subject_requirement text,
  major_remark text,
  match_confidence text
)
language sql
stable
security definer
set search_path = public
as $$
  with query_terms as (
    select array_remove(regexp_split_to_array(coalesce(p_query, ''), '\s*[,，、]\s*'), '') as terms
  ),
  candidate_plans as (
    select p.*
    from public.admission_plans p
    cross join query_terms qt
    where p.year = p_plan_year
      and p.subject = p_subject
      and (
        cardinality(coalesce(p_batches, '{}')) = 0
        or p.batch = any(p_batches)
      )
      and (
        cardinality(coalesce(p_subject_requirements, '{}')) = 0
        or coalesce(nullif(p.subject_requirement, ''), '不限') = any(p_subject_requirements)
      )
      and (
        cardinality(qt.terms) = 0
        or exists (
          select 1
          from unnest(qt.terms) term
          where trim(term) <> ''
            and (
              p.school_name ilike '%' || trim(term) || '%'
              or p.major_name ilike '%' || trim(term) || '%'
              or p.school_code ilike '%' || trim(term) || '%'
              or p.major_code ilike '%' || trim(term) || '%'
              or p.major_remark ilike '%' || trim(term) || '%'
            )
        )
      )
  ),
  candidate_keys as (
    select distinct
      p.subject,
      p.school_name_normalized,
      p.major_name_normalized
    from candidate_plans p
  ),
  history_agg as (
    select
      hh.subject,
      public.normalize_school_name(hh.school_name) as school_name_normalized,
      public.normalize_major_name(hh.major_name) as major_name_normalized,
      count(distinct hh.year)::int as history_years,
      min(hh.min_rank)::int as best_rank,
      max(hh.min_rank)::int as worst_rank,
      round(avg(hh.min_rank))::int as avg_rank,
      ((array_agg(hh.min_score order by hh.year desc, hh.min_rank asc))[1])::int as latest_score,
      ((array_agg(hh.min_rank order by hh.year desc, hh.min_rank asc))[1])::int as latest_rank,
      jsonb_agg(
        jsonb_build_object(
          'year', hh.year,
          'min_score', hh.min_score,
          'min_rank', hh.min_rank,
          'major_code', hh.major_code
        )
        order by hh.year desc
      ) as history
    from public.admission_records hh
    join candidate_keys ck
      on ck.subject = hh.subject
      and ck.school_name_normalized = public.normalize_school_name(hh.school_name)
      and ck.major_name_normalized = public.normalize_major_name(hh.major_name)
    where hh.subject = p_subject
      and hh.year between p_history_year - 2 and p_history_year
      and hh.min_rank is not null
    group by
      hh.subject,
      public.normalize_school_name(hh.school_name),
      public.normalize_major_name(hh.major_name)
  ),
  plan_rows as (
    select
      p.*,
      coalesce(sp_code.school_tags, sp_name.school_tags, p.school_tags) as profile_school_tags,
      coalesce(sp_code.is_985, sp_name.is_985, false) as profile_is_985,
      coalesce(sp_code.is_211, sp_name.is_211, false) as profile_is_211,
      coalesce(sp_code.is_double_first_class, sp_name.is_double_first_class, false) as profile_is_double_first_class,
      coalesce(sp_code.ownership, sp_name.ownership) as profile_ownership,
      loc.province,
      loc.city,
      loc.campus_city,
      h.history_years,
      h.best_rank,
      h.worst_rank,
      h.avg_rank,
      h.latest_score as min_score,
      h.latest_rank as min_rank,
      h.history,
      case when h.worst_rank is null then null else h.worst_rank - p_user_rank end as rank_diff,
      case when h.history_years > 0 then 'normalized_name' else 'none' end as match_confidence
    from candidate_plans p
    left join public.school_profiles sp_code
      on sp_code.school_code = p.school_code
    left join public.school_profiles sp_name
      on sp_code.school_code is null
      and sp_name.school_name_normalized = p.school_name_normalized
    left join public.school_locations loc
      on loc.school_name_normalized = p.school_name_normalized
    left join history_agg h
      on h.subject = p.subject
      and h.school_name_normalized = p.school_name_normalized
      and h.major_name_normalized = p.major_name_normalized
    where (
        cardinality(coalesce(p_provinces, '{}')) = 0
        or loc.province = any(p_provinces)
      )
      and (
        cardinality(coalesce(p_cities, '{}')) = 0
        or loc.city = any(p_cities)
        or coalesce(loc.campus_city, loc.city) = any(p_cities)
      )
      and (
        p_tag = 'all'
        or (
          p_tag = '普通本科'
          and p.batch like '本科%'
          and not coalesce(sp_code.is_985, sp_name.is_985, false)
          and not coalesce(sp_code.is_211, sp_name.is_211, false)
          and not coalesce(sp_code.is_double_first_class, sp_name.is_double_first_class, false)
          and coalesce(sp_code.ownership, sp_name.ownership, '') not in ('民办', '中外合作办学', '内地与港澳台合作办学')
          and not ('民办' = any(coalesce(sp_code.school_tags, sp_name.school_tags, p.school_tags)))
          and not ('民办本科' = any(coalesce(sp_code.school_tags, sp_name.school_tags, p.school_tags)))
          and not ('独立学院' = any(coalesce(sp_code.school_tags, sp_name.school_tags, p.school_tags)))
          and not ('中外合作办学' = any(coalesce(sp_code.school_tags, sp_name.school_tags, p.school_tags)))
          and not ('内地与港澳台地区合作办学' = any(coalesce(sp_code.school_tags, sp_name.school_tags, p.school_tags)))
          and not ('内地与港澳台合作办学' = any(coalesce(sp_code.school_tags, sp_name.school_tags, p.school_tags)))
          and not ('香港' = any(coalesce(sp_code.school_tags, sp_name.school_tags, p.school_tags)))
        )
        or (
          p_tag <> '普通本科'
          and (
            p_tag = any(coalesce(sp_code.school_tags, sp_name.school_tags, p.school_tags))
            or (p_tag = '985' and coalesce(sp_code.is_985, sp_name.is_985, false))
            or (p_tag = '211' and coalesce(sp_code.is_211, sp_name.is_211, false))
            or (p_tag = '双一流' and coalesce(sp_code.is_double_first_class, sp_name.is_double_first_class, false))
            or p.major_name ilike '%' || p_tag || '%'
            or p.major_remark ilike '%' || p_tag || '%'
          )
        )
      )
  ),
  scored as (
    select
      p.*,
      case
        when coalesce(p.history_years, 0) = 0 then 'unknown'
        when p_user_rank <= 0 then 'unknown'
        when p_user_rank <= 20000 and (p.worst_rank - p_user_rank) < -2000 then 'unknown'
        when p_user_rank <= 20000 and (p.worst_rank - p_user_rank) < 0 then 'reach'
        when p_user_rank <= 20000 and (p.worst_rank - p_user_rank) <= 3000 then 'match'
        when p_user_rank <= 20000 then 'safe'
        when p_user_rank <= 80000 and (p.worst_rank - p_user_rank) < -3000 then 'unknown'
        when p_user_rank <= 80000 and (p.worst_rank - p_user_rank) < 0 then 'reach'
        when p_user_rank <= 80000 and (p.worst_rank - p_user_rank) <= 5000 then 'match'
        when p_user_rank <= 80000 then 'safe'
        when (p.worst_rank - p_user_rank) < -5000 then 'unknown'
        when (p.worst_rank - p_user_rank) < 0 then 'reach'
        when (p.worst_rank - p_user_rank) <= 8000 then 'match'
        else 'safe'
      end as risk_type
    from plan_rows p
  ),
  filtered as (
    select *
    from scored
    where p_risk = 'all' or risk_type = p_risk
  )
  select
    f.id,
    f.year,
    f.subject,
    f.school_code,
    f.school_name,
    f.profile_school_tags as school_tags,
    f.province,
    f.city,
    f.campus_city,
    f.major_code,
    f.major_name,
    f.min_score,
    f.min_rank,
    f.plan_nature as admission_type,
    f.major_remark as remark,
    coalesce(f.history_years, 0) as history_years,
    f.best_rank,
    f.worst_rank,
    f.avg_rank,
    f.worst_rank as basis_rank,
    f.rank_diff,
    f.risk_type,
    coalesce(f.history, '[]'::jsonb) as history,
    count(*) over() as total_count,
    f.id as plan_id,
    f.year as plan_year,
    f.batch,
    f.plan_nature,
    f.volunteer_mode,
    f.plan_count,
    f.duration_years,
    f.tuition,
    f.subject_requirement,
    f.major_remark,
    f.match_confidence
  from filtered f
  order by
    case f.risk_type when 'match' then 1 when 'safe' then 2 when 'reach' then 3 else 4 end,
    abs(coalesce(f.rank_diff, 999999999)),
    f.batch,
    f.school_name,
    f.major_code
  limit greatest(1, least(p_limit, 100))
  offset greatest(0, p_offset);
$$;
