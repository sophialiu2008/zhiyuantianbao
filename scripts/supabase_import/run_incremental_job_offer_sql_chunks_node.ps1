param(
  [Parameter(Mandatory = $true)]
  [string]$DatabaseUrl,

  [string]$ChunksDir = "data/enriched/jiuye_feijige_job_data/import_chunks"
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$resolvedChunksDir = Resolve-Path (Join-Path $root $ChunksDir)
$runner = Join-Path $root "scripts/supabase_import/apply_sql_file.cjs"

Get-ChildItem -Path $resolvedChunksDir -Filter "*.sql" |
  Sort-Object Name |
  ForEach-Object {
    Write-Host "Running $($_.Name)"
    node $runner $DatabaseUrl $_.FullName
  }
