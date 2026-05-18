create table if not exists public.major_knowledge_base (
  id bigserial primary key,
  major_name text not null,
  major_name_normalized text not null unique,
  discipline_category text,
  major_category text,
  description text,
  job_directions text[] not null default '{}'::text[],
  further_study_directions text[] not null default '{}'::text[],
  core_courses text[] not null default '{}'::text[],
  suitable_traits text[] not null default '{}'::text[],
  source_note text,
  credibility text not null default '中',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_major_knowledge_normalized
  on public.major_knowledge_base (major_name_normalized);

create index if not exists idx_major_knowledge_name_trgm
  on public.major_knowledge_base using gin (major_name gin_trgm_ops);

alter table public.major_knowledge_base enable row level security;

drop policy if exists "public read major knowledge base" on public.major_knowledge_base;
create policy "public read major knowledge base"
on public.major_knowledge_base for select
to anon, authenticated
using (true);

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
      public.normalize_major_name(trim(coalesce(p_major_query, ''))) as normalized_major_query,
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
        or public.normalize_major_name(mp.major_name) = q.normalized_major_query
        or mp.major_name ilike '%' || q.major_query || '%'
        or q.major_query ilike '%' || mp.major_name || '%'
        or mp.major_code = q.major_query
      )
    order by
      case
        when mp.major_name = q.major_query then 1
        when public.normalize_major_name(mp.major_name) = q.normalized_major_query then 2
        when mp.major_name ilike q.major_query || '%' then 3
        else 4
      end,
      similarity(mp.major_name, q.major_query) desc nulls last,
      length(mp.major_name),
      mp.major_name
    limit 1
  ),
  knowledge_match as (
    select kb.*
    from public.major_knowledge_base kb
    cross join q
    left join major_match mm on true
    where q.normalized_major_query <> ''
      and (
        kb.major_name_normalized = q.normalized_major_query
        or (mm.major_name is not null and kb.major_name_normalized = public.normalize_major_name(mm.major_name))
        or kb.major_name_normalized like '%' || q.normalized_major_query || '%'
        or q.normalized_major_query like '%' || kb.major_name_normalized || '%'
      )
    order by
      case
        when kb.major_name_normalized = q.normalized_major_query then 1
        when mm.major_name is not null and kb.major_name_normalized = public.normalize_major_name(mm.major_name) then 2
        when kb.major_name_normalized like q.normalized_major_query || '%' then 3
        else 4
      end,
      length(kb.major_name_normalized),
      kb.major_name
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
  ),
  profile_payload as (
    select
      to_jsonb(mm)
      || jsonb_build_object(
        'discipline_category', coalesce(nullif(mm.discipline_category, ''), nullif(kb.discipline_category, '')),
        'major_category', coalesce(nullif(mm.major_category, ''), nullif(kb.major_category, '')),
        'description', coalesce(nullif(kb.description, ''), nullif(mm.description, '')),
        'job_directions',
          case
            when coalesce(array_length(kb.job_directions, 1), 0) > 0 then to_jsonb(kb.job_directions)
            else to_jsonb(coalesce(mm.job_directions, '{}'::text[]))
          end,
        'further_study_directions',
          case
            when coalesce(array_length(kb.further_study_directions, 1), 0) > 0 then to_jsonb(kb.further_study_directions)
            else to_jsonb(coalesce(mm.further_study_directions, '{}'::text[]))
          end,
        'knowledge_source_note', kb.source_note,
        'knowledge_credibility', kb.credibility
      ) as profile
    from major_match mm
    left join knowledge_match kb on true
  )
  select coalesce(
    jsonb_build_object(
      'profile', (select profile from profile_payload),
      'schoolMajor', coalesce((select to_jsonb(smp) from school_major smp), '{}'::jsonb),
      'jobs', coalesce((
        select jsonb_agg(to_jsonb(jd) order by jd.data_year desc nulls last, jd.offer_index asc nulls last, jd.id)
        from public.job_data jd
        join q on true
        join school_match sm on true
        join major_match mm on true
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
