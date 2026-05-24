# scripts/setup.ps1
# mmiri28 solutions - mcp-ecosystem setup script
# Run after every git pull.
#
# What it does:
#   1. Finds every MCP folder with a pyproject.toml or package.json
#   2. Runs uv sync (Python) or npm install (Node) if not already done
#   3. Copies .env.example to .env if .env does not exist yet
#   4. Reports which .env files still need credentials filled in
#
# Usage:
#   cd C:\Users\user\Desktop\mcp-ecosystem
#   .\scripts\setup.ps1

param(
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

Write-Host ""
Write-Host "----------------------------------------------------"
Write-Host "  mmiri28 solutions - mcp-ecosystem setup"
Write-Host "----------------------------------------------------"
Write-Host ""

$categories = @("dev", "data", "business", "marketing", "scheduling", "launch", "team", "infra")
$mcpFolders = @()

foreach ($cat in $categories) {
    $catPath = Join-Path $Root $cat
    if (Test-Path $catPath) {
        Get-ChildItem -Path $catPath -Directory | ForEach-Object {
            $hasPy  = Test-Path (Join-Path $_.FullName "pyproject.toml")
            $hasNode = Test-Path (Join-Path $_.FullName "package.json")
            if ($hasPy -or $hasNode) {
                $mcpFolders += [PSCustomObject]@{
                    Name    = $_.Name
                    Path    = $_.FullName
                    Runtime = if ($hasPy) { "python" } else { "node" }
                }
            }
        }
    }
}

Write-Host "  Found $($mcpFolders.Count) MCP(s)"
Write-Host ""

$envNeedsCreds  = @()
$envIncomplete  = @()
$envReady       = @()
$syncFailed     = @()

foreach ($mcp in $mcpFolders) {
    Write-Host "  [ $($mcp.Name) ]"

    $venvExists = Test-Path (Join-Path $mcp.Path ".venv")
    $nodeExists = Test-Path (Join-Path $mcp.Path "node_modules")
    $needsInstall = $Force -or
        ($mcp.Runtime -eq "python" -and -not $venvExists) -or
        ($mcp.Runtime -eq "node"   -and -not $nodeExists)

    if ($needsInstall) {
        Write-Host "      Installing dependencies..."
        try {
            Push-Location $mcp.Path
            if ($mcp.Runtime -eq "python") {
                uv sync --quiet 2>&1 | Out-Null
            } else {
                npm install --silent 2>&1 | Out-Null
            }
            Pop-Location
            Write-Host "      OK - dependencies installed"
        } catch {
            Pop-Location
            Write-Host "      FAILED - $_"
            $syncFailed += $mcp.Name
            continue
        }
    } else {
        Write-Host "      OK - dependencies already installed"
    }

    $envExample = Join-Path $mcp.Path ".env.example"
    $envFile    = Join-Path $mcp.Path ".env"

    if (-not (Test-Path $envExample)) {
        # no .env.example - skip
    } elseif (-not (Test-Path $envFile)) {
        Copy-Item $envExample $envFile
        # Check if the copied file actually has placeholders
        $content = Get-Content $envFile | Where-Object { $_ -notmatch '^s*#' } | Out-String
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
            Write-Host "      NEEDS CREDENTIALS - .env created from example"
            $envNeedsCreds += $mcp.Name
        } else {
            Write-Host "      OK - .env created with working defaults"
            $envReady += $mcp.Name
        }
    } else {
        $content = Get-Content $envFile | Where-Object { $_ -notmatch '^s*#' } | Out-String
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
            Write-Host "      WARNING - .env has placeholder values"
            $envIncomplete += $mcp.Name
        } else {
            Write-Host "      OK - .env ready"
            $envReady += $mcp.Name
        }
    }

    Write-Host ""
}

Write-Host "----------------------------------------------------"
Write-Host "  Summary"
Write-Host ""

if ($envReady.Count -gt 0) {
    Write-Host "  READY ($($envReady.Count)):" -ForegroundColor Green
    $envReady | ForEach-Object { Write-Host "    + $_" -ForegroundColor Green }
    Write-Host ""
}

if ($envNeedsCreds.Count -gt 0) {
    Write-Host "  NEEDS CREDENTIALS ($($envNeedsCreds.Count)):" -ForegroundColor Yellow
    $envNeedsCreds | ForEach-Object { Write-Host "    ! $_ - open its .env and fill in values" -ForegroundColor Yellow }
    Write-Host ""
}

if ($envIncomplete.Count -gt 0) {
    Write-Host "  HAS PLACEHOLDERS ($($envIncomplete.Count)):" -ForegroundColor Yellow
    $envIncomplete | ForEach-Object { Write-Host "    ! $_ - some values still need updating" -ForegroundColor Yellow }
    Write-Host ""
}

if ($syncFailed.Count -gt 0) {
    Write-Host "  INSTALL FAILED ($($syncFailed.Count)):" -ForegroundColor Red
    $syncFailed | ForEach-Object { Write-Host "    x $_ - run uv sync manually in that folder" -ForegroundColor Red }
    Write-Host ""
}

Write-Host "----------------------------------------------------"
Write-Host ""
