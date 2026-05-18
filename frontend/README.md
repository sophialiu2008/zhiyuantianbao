# 河北高考志愿填报工具 Frontend

React + Vite + Supabase 前端。该版本不再全量加载本地 JSON，而是通过 Supabase RPC 分页查询。

## 本地开发

```powershell
cd frontend
copy .env.example .env.local
npm install
npm run dev
```

`.env.local`：

```text
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key
```

## Cloudflare Pages

GitHub 连接 Cloudflare Pages 后使用：

- Root directory: `frontend`
- Build command: `npm run build`
- Build output directory: `dist`
- Environment variables:
  - `VITE_SUPABASE_URL`
  - `VITE_SUPABASE_ANON_KEY`

`public/_redirects` 已配置 SPA fallback，刷新页面不会 404。

## 当前功能

- 分数查位次：调用 `get_rank_record` RPC。
- 推荐列表：调用 `recommend_admissions` RPC。
- 分页查询，每页默认 50 条。
- 支持学校/专业关键词、逗号分隔多专业、冲稳保类型、院校标签筛选。
- 推荐结果展示 2025/2024/2023 三年投档分和位次趋势。
- 院校库支持按学校查询近三年各专业投档分和对应位次，并支持专业关键词过滤。
- 院校对比支持添加 2-4 所院校，并按专业关键词横向比较三年投档趋势。
- 支持学校所在地省份、城市多选筛选。
- 志愿表保存在浏览器 localStorage，并支持导出 CSV、打印另存为 PDF、复制文本、清空。
- 志愿表支持按设备 `device_id` 保存到 Supabase `volunteer_lists` 表，并可从云端恢复。
