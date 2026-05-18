insert into public.school_locations (
  school_name,
  school_name_normalized,
  moe_school_code,
  province,
  city,
  department,
  education_level,
  remark,
  campus_city,
  location_note,
  location_source,
  confidence
) values (
  '电子科技大学(沙河校区)',
  '电子科技大学(沙河校区)',
  null,
  '四川',
  '成都市',
  '教育部',
  '本科',
  null,
  '成都市',
  '沙河校区位于四川省成都市，补充规范化别名以匹配带城市后缀的投档表名称',
  '电子科技大学公开资料',
  'manual'
)
on conflict (school_name_normalized) do update set
  school_name = excluded.school_name,
  province = excluded.province,
  city = excluded.city,
  department = excluded.department,
  education_level = excluded.education_level,
  campus_city = excluded.campus_city,
  location_note = excluded.location_note,
  location_source = excluded.location_source,
  confidence = excluded.confidence;
