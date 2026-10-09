param([switch]$Demo)
$ErrorActionPreference = 'Stop'
$Python = (Get-Command python -ErrorAction Stop).Source
$Pythonw = Join-Path (Split-Path $Python) 'pythonw.exe'
if (-not (Test-Path -LiteralPath $Pythonw)) { throw 'This launcher requires Python with tkinter and pythonw.exe.' }
$Script = Join-Path $PSScriptRoot 'app.py'
$Arguments = @('"' + $Script + '"')
if ($Demo) { $Arguments += '--demo' }
Start-Process -FilePath $Pythonw -ArgumentList $Arguments -WorkingDirectory $PSScriptRoot
