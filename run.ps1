$ErrorActionPreference = 'Stop'
$graphviz = Join-Path $PSScriptRoot '.venv/graphviz/Graphviz-12.2.1-win64/bin'
if (Test-Path (Join-Path $graphviz 'dot.exe')) {
    $env:Path = "$graphviz;$env:Path"
}
python (Join-Path $PSScriptRoot 'main.py') @args
exit $LASTEXITCODE
