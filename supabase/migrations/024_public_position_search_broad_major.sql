create or replace function public.search_public_positions_by_major(
  p_major_query text,
  p_include_low boolean default false,
  p_limit int default 80
)
returns jsonb
language sql
stable
security definer
set search_path = public
as $$
  with q as (
    select public.normalize_major_name(trim(coalesce(p_major_query, ''))) as major_name_normalized
  ),
  matched_major_names as (
    select distinct m.major_name_normalized
    from public.public_position_matches m, q
    where q.major_name_normalized <> ''
      and (
        m.major_name_normalized = q.major_name_normalized
        or m.major_name_normalized like '%' || q.major_name_normalized || '%'
        or q.major_name_normalized like '%' || m.major_name_normalized || '%'
      )
  ),
  matched_ranked as (
    select
      m.*,
      row_number() over (
        partition by m.position_source, m.position_code
        order by
          case m.match_level when 'high' then 1 when 'medium' then 2 else 3 end,
          case
            when m.major_name_normalized = q.major_name_normalized then 1
            when m.major_name_normalized like q.major_name_normalized || '%' then 2
            when m.major_name_normalized like '%' || q.major_name_normalized || '%' then 3
            else 4
          end,
          m.major_name
      ) as rn
    from public.public_position_matches m
    join matched_major_names mm on mm.major_name_normalized = m.major_name_normalized
    cross join q
    where (p_include_low or m.match_level in ('high', 'medium'))
  ),
  matched as (
    select *
    from matched_ranked
    where rn = 1
  ),
  civil_rows as (
    select
      m.match_level,
      m.match_type,
      m.match_reason,
      to_jsonb(p) as position
    from matched m
    join public.civil_service_positions p on p.position_code = m.position_code
    where m.position_source = 'civil_service'
    order by
      case m.match_level when 'high' then 1 when 'medium' then 2 else 3 end,
      p.exam_area,
      p.department,
      p.position_code
    limit greatest(1, least(coalesce(p_limit, 80), 300))
  ),
  military_rows as (
    select
      m.match_level,
      m.match_type,
      m.match_reason,
      to_jsonb(p) as position
    from matched m
    join public.military_civilian_positions p on p.position_code = m.position_code
    where m.position_source = 'military_civilian'
    order by
      case m.match_level when 'high' then 1 when 'medium' then 2 else 3 end,
      p.work_location,
      p.employer_name,
      p.position_code
    limit greatest(1, least(coalesce(p_limit, 80), 300))
  )
  select jsonb_build_object(
    'civilServiceTotal', (select count(*) from matched where position_source = 'civil_service'),
    'militaryCivilianTotal', (select count(*) from matched where position_source = 'military_civilian'),
    'civilService', coalesce((select jsonb_agg(to_jsonb(civil_rows)) from civil_rows), '[]'::jsonb),
    'militaryCivilian', coalesce((select jsonb_agg(to_jsonb(military_rows)) from military_rows), '[]'::jsonb)
  );
$$;
