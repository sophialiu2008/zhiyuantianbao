param(
  [string]$DatabaseUrl = $env:DATABASE_URL
)

$ErrorActionPreference = "Stop"

if (-not $DatabaseUrl) {
  throw "请先提供数据库连接串：.\scripts\supabase_import\run_latest_job_sql_chunks_node.ps1 -DatabaseUrl 'postgresql://...'"
}

$root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$runner = Join-Path $root "scripts\supabase_import\run_latest_job_sql_chunks.cjs"

node $runner $DatabaseUrl
if ($LASTEXITCODE -ne 0) {
  throw "SQL 批量执行失败。"
}
