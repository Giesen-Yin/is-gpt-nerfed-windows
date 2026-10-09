param([Parameter(ValueFromRemainingArguments=$true)][string[]]$Args)
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Script = Join-Path $Root 'plugin\skills\is-gpt-nerfed\scripts\nerfed'
$Python = Get-Command python -ErrorAction SilentlyContinue
if (-not $Python) { $Python = Get-Command py -ErrorAction SilentlyContinue }
if (-not $Python) { throw 'Python 3.11+ is required.' }
$PythonArgs = @()
if ($Python.Name -in @('py','py.exe')) { $PythonArgs = @('-3') }
& $Python.Source @PythonArgs -c "import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)"
if ($LASTEXITCODE -ne 0) { throw 'Python 3.11+ is required.' }
& $Python.Source @PythonArgs $Script teardown @Args
exit $LASTEXITCODE
