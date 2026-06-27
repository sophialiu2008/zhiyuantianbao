drop function if exists public.recommend_admission_plans(
  int, int, text, int, text, text, text, int, int, text[], text[], text[], text[]
);

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
  match_confidence text,
  is_new_major boolean,
  history_match_note text
)
language sql
stable
security definer
set search_path = public
as $$
  with query_terms as (
    select array_remove(regexp_split_to_array(coalesce(p_query, ''), '\s*[,，、\s]\s*'), '') as terms
  ),
  candidate_plans as (
    select p.*
    from public.admission_plans p
    cross join query_terms qt
    where p.year = p_plan_year
      and p.subject = p_subject
      and (cardinality(coalesce(p_batches, '{}')) = 0 or p.batch = any(p_batches))
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
      and (
        cardinality(coalesce(p_provinces, '{}')) = 0
        or exists (
          select 1
          from public.school_locations loc
          where loc.school_name_normalized = p.school_name_normalized
            and loc.province = any(p_provinces)
        )
      )
      and (
        cardinality(coalesce(p_cities, '{}')) = 0
        or exists (
          select 1
          from public.school_locations loc
          where loc.school_name_normalized = p.school_name_normalized
            and (loc.city = any(p_cities) or coalesce(loc.campus_city, loc.city) = any(p_cities))
        )
      )
      and (
        p_tag = 'all'
        or (
          p_tag = '普通本科'
          and p.batch like '本科%'
          and not ('民办' = any(p.school_tags))
          and not ('民办本科' = any(p.school_tags))
          and not ('独立学院' = any(p.school_tags))
          and not ('中外合作办学' = any(p.school_tags))
          and not ('内地与港澳台地区合作办学' = any(p.school_tags))
          and not ('内地与港澳台合作办学' = any(p.school_tags))
          and not ('香港' = any(p.school_tags))
          and not exists (
            select 1
            from public.school_profiles sp
            where (sp.school_code = p.school_code or sp.school_name_normalized = p.school_name_normalized)
              and (
                coalesce(sp.is_985, false)
                or coalesce(sp.is_211, false)
                or coalesce(sp.is_double_first_class, false)
                or coalesce(sp.ownership, '') in ('民办', '中外合作办学', '内地与港澳台合作办学')
              )
          )
        )
        or (
          p_tag <> '普通本科'
          and (
            p_tag = any(p.school_tags)
            or p.major_name ilike '%' || p_tag || '%'
            or p.major_remark ilike '%' || p_tag || '%'
            or exists (
              select 1
              from public.school_profiles sp
              where (sp.school_code = p.school_code or sp.school_name_normalized = p.school_name_normalized)
                and (
                  p_tag = any(sp.school_tags)
                  or (p_tag = '985' and coalesce(sp.is_985, false))
                  or (p_tag = '211' and coalesce(sp.is_211, false))
                  or (p_tag = '双一流' and coalesce(sp.is_double_first_class, false))
                )
            )
          )
        )
      )
  ),
  plan_rows as (
    select
      p.*,
      coalesce(pm.history_years, 0) as history_years,
      pm.best_rank,
      pm.worst_rank,
      pm.avg_rank,
      pm.latest_score as min_score,
      pm.latest_rank as min_rank,
      coalesce(
        (
          select jsonb_agg(
            jsonb_build_object(
              'year', history_year,
              'min_score', min_score,
              'min_rank', min_rank
            )
            order by history_year desc
          )
          from (
            values
              (2025, pm.min_score_2025, pm.min_rank_2025),
              (2024, pm.min_score_2024, pm.min_rank_2024),
              (2023, pm.min_score_2023, pm.min_rank_2023)
          ) as snapshot(history_year, min_score, min_rank)
          where snapshot.min_rank is not null
        ),
        '[]'::jsonb
      ) as history,
      case
        when pm.worst_rank is null then null
        else pm.worst_rank - p_user_rank
      end as rank_diff,
      case when pm.id is not null then 'precomputed_xlsx' else 'none' end as match_confidence,
      coalesce(pm.is_new_major, false) as is_new_major,
      coalesce(pm.match_note, '') as history_match_note
    from candidate_plans p
    left join public.admission_plan_history_matches pm
      on pm.plan_year = p.year
      and pm.subject = p.subject
      and pm.batch = p.batch
      and pm.school_code = p.school_code
      and pm.major_code = p.major_code
      and pm.major_name = p.major_name
      and pm.major_remark = p.major_remark
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
  ),
  page_rows as (
    select
      f.*,
      count(*) over() as total_count
    from filtered f
    order by
      case f.risk_type when 'match' then 1 when 'safe' then 2 when 'reach' then 3 else 4 end,
      abs(coalesce(f.rank_diff, 999999999)),
      f.batch,
      f.school_name,
      f.major_code
    limit greatest(1, least(p_limit, 100))
    offset greatest(0, p_offset)
  )
  select
    f.id,
    f.year,
    f.subject,
    f.school_code,
    f.school_name,
    coalesce(sp_code.school_tags, sp_name.school_tags, f.school_tags) as school_tags,
    loc.province,
    loc.city,
    loc.campus_city,
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
    f.total_count,
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
    f.match_confidence,
    f.is_new_major,
    f.history_match_note
  from page_rows f
  left join public.school_profiles sp_code
    on sp_code.school_code = f.school_code
  left join public.school_profiles sp_name
    on sp_code.school_code is null
    and sp_name.school_name_normalized = f.school_name_normalized
  left join public.school_locations loc
    on loc.school_name_normalized = f.school_name_normalized
  order by
    case f.risk_type when 'match' then 1 when 'safe' then 2 when 'reach' then 3 else 4 end,
    abs(coalesce(f.rank_diff, 999999999)),
    f.batch,
    f.school_name,
    f.major_code;
$$;

notify pgrst, 'reload schema';
