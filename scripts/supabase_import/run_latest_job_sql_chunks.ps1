param(
  [string]$DatabaseUrl = $env:DATABASE_URL
)

$ErrorActionPreference = "Stop"

if (-not $DatabaseUrl) {
  throw "请先提供数据库连接串：.\scripts\supabase_import\run_latest_job_sql_chunks.ps1 -DatabaseUrl 'postgresql://...'"
}

$psql = Get-Command psql -ErrorAction SilentlyContinue
if (-not $psql) {
  throw "未找到 psql。请先安装 PostgreSQL 客户端，或把 psql.exe 所在目录加入 PATH。"
}

$root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$schemaFile = Join-Path $root "supabase\migrations\019_latest_job_offer_schema.sql"
$chunkDir = Join-Path $root "data\enriched\latest_job_data\import_chunks"

if (-not (Test-Path -LiteralPath $schemaFile)) {
  throw "找不到 schema 文件：$schemaFile"
}

if (-not (Test-Path -LiteralPath $chunkDir)) {
  throw "找不到导入分片目录：$chunkDir"
}

$files = @()
$files += Get-Item -LiteralPath $schemaFile
$files += Get-ChildItem -LiteralPath $chunkDir -Filter "*.sql" | Sort-Object Name

Write-Host "将执行 $($files.Count) 个 SQL 文件。" -ForegroundColor Cyan

foreach ($file in $files) {
  Write-Host "执行：$($file.FullName)" -ForegroundColor Cyan
  & $psql.Source $DatabaseUrl -v ON_ERROR_STOP=1 -f $file.FullName
  if ($LASTEXITCODE -ne 0) {
    throw "SQL 执行失败：$($file.FullName)"
  }
}

Write-Host "全部 SQL 文件执行完成。" -ForegroundColor Green
