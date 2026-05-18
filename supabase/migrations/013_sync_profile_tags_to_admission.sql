update public.admission_records a
set school_tags = coalesce(sp.school_tags, a.school_tags)
from public.school_profiles sp
where sp.school_code = a.school_code
  and coalesce(sp.school_tags, '{}'::text[]) <> '{}'::text[];

