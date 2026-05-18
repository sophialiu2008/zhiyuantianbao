create or replace function public.get_school_profile(
  p_school_query text,
  p_subject text default 'physics'
)
returns table (
  school_name text,
  school_tags text[],
  province text,
  city text,
  campus_city text,
  major_code text,
  major_name text,
  latest_year int,
  latest_score int,
  latest_rank int,
  history_years int,
  history jsonb
)
language sql
stable
security definer
set search_path = public
as $$
  with terms as (
    select
      trim(coalesce(p_school_query, '')) as raw_query,
      public.normalize_school_name(trim(coalesce(p_school_query, ''))) as normalized_query
  ),
  matched as (
    select
      a.*,
      loc.province,
      loc.city,
      loc.campus_city,
      public.normalize_school_name(a.school_name) as normalized_school_name
    from public.admission_records a
    left join public.school_locations loc
      on loc.school_name_normalized = public.normalize_school_name(a.school_name)
      or loc.school_name_normalized = replace(replace(a.school_name, '（', '('), '）', ')')
    cross join terms t
    where t.raw_query <> ''
      and a.subject = p_subject
      and a.min_score is not null
      and a.min_rank is not null
      and (
        public.normalize_school_name(a.school_name) = t.normalized_query
        or public.normalize_school_name(a.school_name) ilike '%' || t.normalized_query || '%'
        or a.school_name ilike '%' || t.raw_query || '%'
      )
  ),
  grouped as (
    select
      normalized_school_name,
      major_name,
      (array_agg(school_name order by year desc, min_rank asc))[1] as school_name,
      (array_agg(array_to_string(school_tags, chr(31)) order by year desc, min_rank asc))[1] as school_tags_text,
      (array_agg(province order by year desc, min_rank asc))[1] as province,
      (array_agg(city order by year desc, min_rank asc))[1] as city,
      (array_agg(campus_city order by year desc, min_rank asc))[1] as campus_city,
      (array_agg(major_code order by year desc, min_rank asc))[1] as major_code,
      (array_agg(year order by year desc, min_rank asc))[1] as latest_year,
      (array_agg(min_score order by year desc, min_rank asc))[1] as latest_score,
      (array_agg(min_rank order by year desc, min_rank asc))[1] as latest_rank,
      count(distinct year)::int as history_years,
      jsonb_agg(
        jsonb_build_object(
          'year', year,
          'min_score', min_score,
          'min_rank', min_rank,
          'major_code', major_code
        )
        order by year desc
      ) as history
    from matched
    group by normalized_school_name, major_name
  )
  select
    g.school_name,
    case
      when coalesce(g.school_tags_text, '') = '' then '{}'::text[]
      else string_to_array(g.school_tags_text, chr(31))
    end as school_tags,
    g.province,
    g.city,
    g.campus_city,
    g.major_code,
    g.major_name,
    g.latest_year,
    g.latest_score,
    g.latest_rank,
    g.history_years,
    g.history
  from grouped g
  order by g.latest_rank asc nulls last, g.major_name
  limit 500;
$$;
