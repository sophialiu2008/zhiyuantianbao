create or replace function public.recommend_admissions(
  p_year int,
  p_subject text,
  p_user_rank int,
  p_query text default '',
  p_risk text default 'all',
  p_tag text default 'all',
  p_limit int default 50,
  p_offset int default 0,
  p_provinces text[] default '{}',
  p_cities text[] default '{}'
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
  total_count bigint
)
language sql
stable
security definer
set search_path = public
as $$
  with query_terms as (
    select array_remove(regexp_split_to_array(coalesce(p_query, ''), '\s*[,，、]\s*'), '') as terms
  ),
  current_rows as (
    select
      a.*,
      coalesce(sp.school_tags, a.school_tags) as profile_school_tags,
      coalesce(sp.is_985, false) as profile_is_985,
      coalesce(sp.is_211, false) as profile_is_211,
      coalesce(sp.is_double_first_class, false) as profile_is_double_first_class,
      sp.ownership as profile_ownership,
      loc.province,
      loc.city,
      loc.campus_city
    from public.admission_records a
    left join public.school_profiles sp
      on sp.school_code = a.school_code
    left join public.school_locations loc
      on loc.school_name_normalized = public.normalize_school_name(a.school_name)
      or loc.school_name_normalized = replace(replace(a.school_name, '（', '('), '）', ')')
    cross join query_terms qt
    where a.year = p_year
      and a.subject = p_subject
      and a.min_score is not null
      and a.min_rank is not null
      and (
        cardinality(qt.terms) = 0
        or exists (
          select 1
          from unnest(qt.terms) term
          where trim(term) <> ''
            and (
              a.school_name ilike '%' || trim(term) || '%'
              or a.major_name ilike '%' || trim(term) || '%'
              or a.school_code ilike '%' || trim(term) || '%'
              or a.major_code ilike '%' || trim(term) || '%'
            )
        )
      )
      and (
        p_tag = 'all'
        or (
          p_tag = '普通本科'
          and not coalesce(sp.is_985, false)
          and not coalesce(sp.is_211, false)
          and not coalesce(sp.is_double_first_class, false)
          and coalesce(sp.ownership, '') not in ('民办', '中外合作办学', '内地与港澳台合作办学')
          and not ('民办' = any(coalesce(sp.school_tags, a.school_tags)))
          and not ('民办本科' = any(coalesce(sp.school_tags, a.school_tags)))
          and not ('独立学院' = any(coalesce(sp.school_tags, a.school_tags)))
          and not ('中外合作办学' = any(coalesce(sp.school_tags, a.school_tags)))
          and not ('内地与港澳台地区合作办学' = any(coalesce(sp.school_tags, a.school_tags)))
          and not ('内地与港澳台合作办学' = any(coalesce(sp.school_tags, a.school_tags)))
          and not ('香港' = any(coalesce(sp.school_tags, a.school_tags)))
        )
        or (
          p_tag <> '普通本科'
          and (
            p_tag = any(coalesce(sp.school_tags, a.school_tags))
            or (p_tag = '985' and coalesce(sp.is_985, false))
            or (p_tag = '211' and coalesce(sp.is_211, false))
            or (p_tag = '双一流' and coalesce(sp.is_double_first_class, false))
            or a.major_name ilike '%' || p_tag || '%'
          )
        )
      )
      and (
        cardinality(coalesce(p_provinces, '{}')) = 0
        or loc.province = any(p_provinces)
      )
      and (
        cardinality(coalesce(p_cities, '{}')) = 0
        or loc.city = any(p_cities)
        or coalesce(loc.campus_city, loc.city) = any(p_cities)
      )
  ),
  scored as (
    select
      c.*,
      h.history_years,
      h.best_rank,
      h.worst_rank,
      h.avg_rank,
      h.history,
      h.worst_rank as basis_rank,
      (h.worst_rank - p_user_rank) as rank_diff,
      case
        when h.history_years = 0 then 'unknown'
        when p_user_rank <= 20000 and (h.worst_rank - p_user_rank) < -2000 then 'unknown'
        when p_user_rank <= 20000 and (h.worst_rank - p_user_rank) < 0 then 'reach'
        when p_user_rank <= 20000 and (h.worst_rank - p_user_rank) <= 3000 then 'match'
        when p_user_rank <= 20000 then 'safe'
        when p_user_rank <= 80000 and (h.worst_rank - p_user_rank) < -3000 then 'unknown'
        when p_user_rank <= 80000 and (h.worst_rank - p_user_rank) < 0 then 'reach'
        when p_user_rank <= 80000 and (h.worst_rank - p_user_rank) <= 5000 then 'match'
        when p_user_rank <= 80000 then 'safe'
        when (h.worst_rank - p_user_rank) < -5000 then 'unknown'
        when (h.worst_rank - p_user_rank) < 0 then 'reach'
        when (h.worst_rank - p_user_rank) <= 8000 then 'match'
        else 'safe'
      end as risk_type
    from current_rows c
    cross join lateral (
      select
        count(distinct hh.year)::int as history_years,
        min(hh.min_rank)::int as best_rank,
        max(hh.min_rank)::int as worst_rank,
        round(avg(hh.min_rank))::int as avg_rank,
        jsonb_agg(
          jsonb_build_object(
            'year', hh.year,
            'min_score', hh.min_score,
            'min_rank', hh.min_rank
          )
          order by hh.year desc
        ) as history
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
    f.profile_school_tags as school_tags,
    f.province,
    f.city,
    f.campus_city,
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
    f.history,
    count(*) over() as total_count
  from filtered f
  order by
    case f.risk_type when 'match' then 1 when 'safe' then 2 when 'reach' then 3 else 4 end,
    abs(f.rank_diff),
    f.min_rank
  limit greatest(1, least(p_limit, 100))
  offset greatest(0, p_offset);
$$;
