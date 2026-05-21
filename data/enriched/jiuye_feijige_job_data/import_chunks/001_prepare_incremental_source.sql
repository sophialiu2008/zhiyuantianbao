insert into public.data_sources (source_key, source_name, source_type, source_year, credibility, update_frequency, notes)
values ('jiuye_feijige_offer_extract_2026', 'jiuye_feijige_offer_extract.xlsx', '视频转写/OCR整理就业offer', 2026, '中', '按批次更新', '就业飞机哥视频提取结果；语音转写和画面字幕OCR仅作离线参考，不作为正式字段入库；按院校+专业与既有job_data去重后增量补充')
on conflict (source_key) do update set
  source_name = excluded.source_name,
  source_type = excluded.source_type,
  source_year = excluded.source_year,
  credibility = excluded.credibility,
  update_frequency = excluded.update_frequency,
  notes = excluded.notes;

delete from public.latest_job_offer_import_staging
where import_batch = '就业飞机哥_2026_20260521';
