# 河北高考志愿填报工具

面向河北省新高考志愿填报的本地数据清洗 + Supabase 数据查询 + React/Vite 前端项目。

## 目录

```text
app/                       早期静态原型，保留作参考
data/cleaned/              Excel 清洗后的 JSON/CSV
frontend/                  React + Vite 前端
scripts/data_cleaning/     Excel 清洗脚本
scripts/supabase_import/   Supabase 数据导入脚本
supabase/migrations/       数据库表结构和 RPC
```

## 推荐开发流程

1. 运行 Excel 清洗：

```powershell
& 'C:\Users\liuli\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' scripts\data_cleaning\clean_excel.py --input . --output data\cleaned
```

2. 在 Supabase 执行：

```text
supabase/migrations/001_init_gaokao.sql
```

3. 导入数据：

```powershell
$env:SUPABASE_DB_URL="postgresql://..."
python scripts\supabase_import\import_cleaned_data.py --data data\cleaned --truncate
```

4. 配置前端：

```powershell
cd frontend
copy .env.example .env.local
npm install
npm run dev
```

## Zeabur 部署

代码推送到 GitHub 后，在 Zeabur 中连接仓库：

- 仓库：`sophialiu2008/zhiyuantianbao`
- Root directory: 留空，使用根目录 `package.json`
- Install command: `npm install`
- Build command: `npm run build`
- Start command: `npm start`
- 环境变量：`VITE_SUPABASE_URL`、`VITE_SUPABASE_ANON_KEY`

根目录脚本会自动转到 `frontend` 执行安装、构建和预览服务。

## Android 后续路线

Web 版稳定后再接 Capacitor：

```powershell
cd frontend
npm install @capacitor/cli @capacitor/core @capacitor/android
npx cap init
npx cap add android
npm run build
npx cap sync android
npx cap open android
```
