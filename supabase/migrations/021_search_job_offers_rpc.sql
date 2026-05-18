create or replace function public.search_job_offers(
  p_school_query text default '',
  p_major_query text default '',
  p_degree_level text default 'all',
  p_data_year int default null,
  p_company_query text default '',
  p_limit int default 80,
  p_offset int default 0
)
returns jsonb
language sql
stable
security definer
set search_path = public
as '
  with filtered as (
    select *
    from public.job_data
    where credibility in (''高'', ''中'')
      and verification_status in (''verified'', ''reviewed'')
      and (coalesce(trim(p_school_query), '''') = '''' or school_name ilike ''%'' || trim(p_school_query) || ''%'')
      and (coalesce(trim(p_major_query), '''') = '''' or major_name ilike ''%'' || trim(p_major_query) || ''%'')
      and (coalesce(p_degree_level, ''all'') = ''all'' or degree_level = p_degree_level)
      and (p_data_year is null or data_year = p_data_year)
      and (
        coalesce(trim(p_company_query), '''') = ''''
        or company_name_standard ilike ''%'' || trim(p_company_query) || ''%''
        or company_name_raw ilike ''%'' || trim(p_company_query) || ''%''
        or exists (
          select 1
          from unnest(employers) employer
          where employer ilike ''%'' || trim(p_company_query) || ''%''
        )
      )
  ),
  paged as (
    select *
    from filtered
    order by data_year desc nulls last, school_name, major_name, degree_level, offer_index nulls last, id
    limit greatest(1, least(coalesce(p_limit, 80), 200))
    offset greatest(0, coalesce(p_offset, 0))
  )
  select jsonb_build_object(
    ''total'', (select count(*) from filtered),
    ''records'', coalesce((select jsonb_agg(to_jsonb(paged) order by data_year desc nulls last, school_name, major_name, degree_level, offer_index nulls last, id) from paged), ''[]''::jsonb)
  );
';
