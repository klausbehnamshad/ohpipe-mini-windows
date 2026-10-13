# oh-kette Starter (PowerShell 5.1/7). Aufruf mit vollem Pfad moeglich.
param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Args)
$root = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
& "$root\runtime\python\python.exe" "$root\app\ohpipe.py" kette @Args
