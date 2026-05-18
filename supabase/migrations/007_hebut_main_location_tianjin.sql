update public.school_locations
set
  province = '天津',
  city = '天津市',
  campus_city = null,
  location_note = '河北工业大学隶属河北省，主校区实际所在地按天津市处理，便于按就读城市筛选',
  location_source = '人工校正',
  confidence = 'manual'
where school_name_normalized = '河北工业大学';
