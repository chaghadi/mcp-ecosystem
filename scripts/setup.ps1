# scripts/setup.ps1
# ─────────────────────────────────────────────────────────────────────────────
# mmiri28 solutions — mcp-ecosystem setup script
# Run this once after every git pull.
#
# What it does:
#   1. Finds every MCP folder that has a pyproject.toml or package.json
#   2. Runs uv sync (Python) or npm install (Node) if not already done
#   3. Copies .env.example to .env if .env does not exist yet
#   4. Reports which .env files still need credentials filled in
#
# Usage:
#   cd C:\Users\user\Desktop\mcp-ecosystem
#   .\scripts\setup.ps1
# ─────────────────────────────────────────────────────────────────────────────

param(
    [switch]$Force  # Re-run uv sync even if .venv already exists
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

# ── Colours ───────────────────────────────────────────────────────────────────
function Write-Ok($msg)   { Write-Host "  ✅ $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "  ⚠️  $msg" -ForegroundColor Yellow }
function Write-Info($msg) { Write-Host "  →  $msg" -ForegroundColor Cyan }
function Write-Err($msg)  { Write-Host "  ❌ $msg" -ForegroundColor Red }

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray
Write-Host "  mmiri28 solutions — mcp-ecosystem setup" -ForegroundColor White
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray
Write-Host ""

# ── Find all MCP folders ──────────────────────────────────────────────────────
$categories = @("dev", "data", "business", "marketing", "scheduling", "launch", "team", "infra")
$mcpFolders = @()

foreach ($cat in $categories) {
    $catPath = Join-Path $Root $cat
    if (Test-Path $catPath) {
        Get-ChildItem -Path $catPath -Directory | ForEach-Object {
            $hasPyproject  = Test-Path (Join-Path $_.FullName "pyproject.toml")
            $hasPackageJson = Test-Path (Join-Path $_.FullName "package.json")
            if ($hasPyproject -or $hasPackageJson) {
                $mcpFolders += [PSCustomObject]@{
                    Name     = $_.Name
                    Path     = $_.FullName
                    Runtime  = if ($hasPyproject) { "python" } else { "node" }
                }
            }
        }
    }
}

Write-Host "  Found $($mcpFolders.Count) MCP(s)" -ForegroundColor White
Write-Host ""

# ── Track .env status for final report ───────────────────────────────────────
$envMissing     = @()  # .env does not exist (just copied from example)
$envIncomplete  = @()  # .env exists but has placeholder values
$envReady       = @()  # .env looks filled in
$syncFailed     = @()  # uv sync or npm install failed

foreach ($mcp in $mcpFolders) {
    Write-Host "  $($mcp.Name)" -ForegroundColor White

    # ── 1. Install dependencies ───────────────────────────────────────────────
    $venvExists = Test-Path (Join-Path $mcp.Path ".venv")
    $nodeExists = Test-Path (Join-Path $mcp.Path "node_modules")

    $needsInstall = $Force -or
        ($mcp.Runtime -eq "python" -and -not $venvExists) -or
        ($mcp.Runtime -eq "node"   -and -not $nodeExists)

    if ($needsInstall) {
        Write-Info "Installing dependencies..."
        try {
            Push-Location $mcp.Path
            if ($mcp.Runtime -eq "python") {
                uv sync --quiet 2>&1 | Out-Null
            } else {
                npm install --silent 2>&1 | Out-Null
            }
            Pop-Location
            Write-Ok "Dependencies installed"
        } catch {
            Pop-Location
            Write-Err "Install failed: $_"
            $syncFailed += $mcp.Name
            continue
        }
    } else {
        Write-Ok "Dependencies already installed"
    }

    # ── 2. Copy .env.example → .env ───────────────────────────────────────────
    $envExample = Join-Path $mcp.Path ".env.example"
    $envFile    = Join-Path $mcp.Path ".env"

    if (-not (Test-Path $envExample)) {
        # No .env.example — skip silently
    } elseif (-not (Test-Path $envFile)) {
        Copy-Item $envExample $envFile
        Write-Warn ".env created from example — needs credentials"
        $envMissing += $mcp.Name
    } else {
        # Check for unfilled placeholder values
        $content = Get-Content $envFile -Raw
        $placeholders = @(
            "your-password", "your-account-id", "your-access-key",
            "your-secret", "your-endpoint", "your-project",
            "[PASSWORD]", "[YOUR-", "placeholder", "changeme"
        )
        $hasPlaceholder = $false
        foreach ($p in $placeholders) {
            if ($content -match [regex]::Escape($p)) {
                $hasPlaceholder = $true
                break
            }
        }
        if ($hasPlaceholder) {
            Write-Warn ".env exists but has placeholder values"
            $envIncomplete += $mcp.Name
        } else {
            Write-Ok ".env ready"
            $envReady += $mcp.Name
        }
    }

    Write-Host ""
}

# ── Final report ──────────────────────────────────────────────────────────────
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray
Write-Host "  Setup complete" -ForegroundColor White
Write-Host ""

if ($envReady.Count -gt 0) {
    Write-Host "  Ready ($($envReady.Count)):" -ForegroundColor Green
    $envReady | ForEach-Object { Write-Host "    ✅ $_" -ForegroundColor Green }
    Write-Host ""
}

if ($envMissing.Count -gt 0) {
    Write-Host "  Needs credentials ($($envMissing.Count)):" -ForegroundColor Yellow
    $envMissing | ForEach-Object { Write-Host "    ⚠️  $_ — open data\$_\.env and fill in values" -ForegroundColor Yellow }
    Write-Host ""
}

if ($envIncomplete.Count -gt 0) {
    Write-Host "  Has placeholder values ($($envIncomplete.Count)):" -ForegroundColor Yellow
    $envIncomplete | ForEach-Object { Write-Host "    ⚠️  $_ — some values still need updating" -ForegroundColor Yellow }
    Write-Host ""
}

if ($syncFailed.Count -gt 0) {
    Write-Host "  Install failed ($($syncFailed.Count)):" -ForegroundColor Red
    $syncFailed | ForEach-Object { Write-Host "    ❌ $_ — run uv sync manually in that folder" -ForegroundColor Red }
    Write-Host ""
}

Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray
Write-Host ""
