# Supabase 配置说明

## 1. 创建项目

在 Supabase 创建一个新项目，记录：

- Project URL
- anon public key
- Database connection string

前端只使用 anon key。导入数据时使用数据库连接串，不要提交到 GitHub。

## 2. 执行表结构

在 Supabase SQL Editor 执行：

```text
supabase/migrations/001_init_gaokao.sql
```

这个迁移会创建：

- `rank_table`
- `admission_records`
- `data_import_batches`
- `volunteer_lists`
- 查询索引
- 只读 RLS 策略
- `get_rank_record` RPC
- `recommend_admissions` RPC

## 3. 导入清洗数据

先确认本地已经生成：

```text
data/cleaned/rank_table/all_rank.json
data/cleaned/admission/all_admission.json
```

安装导入依赖：

```powershell
pip install "psycopg[binary]"
```

设置连接串并导入：

```powershell
$env:SUPABASE_DB_URL="postgresql://..."
python scripts\supabase_import\import_cleaned_data.py --data data\cleaned --truncate
```

## 4. 验证 SQL

在 Supabase SQL Editor 运行：

```sql
select * from public.get_rank_record(2025, 'physics', 628);
```

应返回：

```text
cumulative_rank = 10271
```

再运行：

```sql
select *
from public.recommend_admissions(
  2025,
  'physics',
  10271,
  '北京林业大学',
  'all',
  'all',
  10,
  0
);
```

应能返回北京林业大学相关专业推荐。

