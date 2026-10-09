param([string]$IntegrationCodex)
$ErrorActionPreference = 'Stop'
$Root = Split-Path $PSScriptRoot -Parent
Push-Location $Root
try {
    $Version = (Get-Content (Join-Path $Root 'plugin/.codex-plugin/plugin.json') -Raw | ConvertFrom-Json).version
    python -m PyInstaller --noconfirm --workpath dist/build --distpath "dist/releases/$Version" windows/IsGPTNerfed.spec
    if ($LASTEXITCODE -ne 0) { throw 'EXE build failed' }
    python windows/test_bundle.py --bundle "dist/releases/$Version/IsGPTNerfed"
    if ($LASTEXITCODE -ne 0) { throw 'Bundle verification failed' }
    if ($IntegrationCodex) {
        python windows/test_installation.py --bundle "dist/releases/$Version/IsGPTNerfed" --codex $IntegrationCodex
        if ($LASTEXITCODE -ne 0) { throw 'Isolated native installation verification failed' }
    }
    python windows/package_release.py
    if ($LASTEXITCODE -ne 0) { throw 'Release packaging failed' }
    Write-Host "Built: $Root\dist\releases\$Version\IsGPTNerfed\IsGPTNerfed.exe"
} finally { Pop-Location }
