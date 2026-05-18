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
  with query_terms as (
    select array_remove(
      array(
        select trim(term)
        from regexp_split_to_table(coalesce(p_query, ''), '[,，、;；\\s]+') as term
        where trim(term) <> ''
      ),
      ''
    ) as terms
  ),
  current_rows as (
    select a.*
    from public.admission_records a
    cross join query_terms q
    where a.year = p_year
      and a.subject = p_subject
      and a.min_score is not null
      and a.min_rank is not null
      and (
        cardinality(q.terms) = 0
        or exists (
          select 1
          from unnest(q.terms) as term
          where a.school_name ilike '%' || term || '%'
             or a.major_name ilike '%' || term || '%'
             or a.school_code ilike '%' || term || '%'
             or a.major_code ilike '%' || term || '%'
        )
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
