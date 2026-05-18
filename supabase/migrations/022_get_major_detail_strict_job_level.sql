create or replace function public.get_major_detail(
  p_major_query text,
  p_school_query text default '',
  p_subject text default 'physics',
  p_degree_level text default '本科'
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
      public.normalize_school_name(trim(coalesce(p_school_query, ''))) as normalized_school_query,
      coalesce(nullif(trim(p_degree_level), ''), '本科') as degree_level
  ),
  major_match as (
    select mp.*
    from public.major_profiles mp, q
    where q.major_query <> ''
      and (
        mp.major_name = q.major_query
        or mp.major_name ilike '%' || q.major_query || '%'
        or mp.major_code = q.major_query
      )
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
    where a.subject = p_subject
      and a.min_rank is not null
    group by a.school_code, a.major_name
    order by best_rank asc
    limit 20
  )
  select coalesce(
    jsonb_build_object(
      'profile', to_jsonb(mm),
      'schoolMajor', coalesce((select to_jsonb(smp) from school_major smp), '{}'::jsonb),
      'jobs', coalesce((
        select jsonb_agg(to_jsonb(jd) order by jd.data_year desc nulls last, jd.offer_index asc nulls last, jd.id)
        from public.job_data jd
        join q on true
        join school_match sm on true
        where q.school_query <> ''
          and (
            jd.major_name = q.major_query
            or jd.major_name = mm.major_name
            or jd.major_code = mm.major_code
          )
          and jd.degree_level = q.degree_level
          and (
            jd.school_code = sm.school_code
            or public.normalize_school_name(jd.school_name) = sm.school_name_normalized
          )
          and jd.credibility in ('高','中')
          and jd.verification_status in ('verified','reviewed')
      ), '[]'::jsonb),
      'schoolCompare', coalesce((select jsonb_agg(to_jsonb(ac) order by ac.best_rank asc) from admission_compare ac), '[]'::jsonb)
    ),
    '{}'::jsonb
  )
  from major_match mm;
$$;
