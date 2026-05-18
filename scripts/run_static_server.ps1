$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$node = "C:\Users\liuli\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe"
$port = if ($args.Count -gt 0) { $args[0] } else { "8790" }

Set-Location -LiteralPath $root
Write-Host "Serving $root"
Write-Host "Open http://127.0.0.1:$port/app/"
& $node scripts\static_server.mjs $port
