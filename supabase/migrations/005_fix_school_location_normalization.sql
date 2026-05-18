create or replace function public.normalize_school_name(p_name text)
returns text
language sql
immutable
as $$
  select regexp_replace(
    trim(
      regexp_replace(
        regexp_replace(
          regexp_replace(
            regexp_replace(coalesce(p_name, ''), '\[[^\]]*\]', '', 'g'),
            '（', '(',
            'g'
          ),
          '）',
          ')',
          'g'
        ),
        '\(([^)]*(市|地方专项|中外合作|按高考|八协|少数民族预科|国际合作|国际本科学术互认|京津冀职教)[^)]*)\)',
        '',
        'g'
      )
    ),
    '\s+',
    '',
    'g'
  );
$$;

comment on function public.normalize_school_name(text) is
  'Normalize admission school names for location matching. City/admission-plan suffixes are removed, real campus suffixes such as 威海校区 and 荣昌校区 are preserved.';
