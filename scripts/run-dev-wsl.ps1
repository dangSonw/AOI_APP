$ErrorActionPreference = 'Stop'

$projectWindowsPath = (Get-Item (Join-Path $PSScriptRoot '..')).FullName
$wslUncPattern = '^\\\\wsl(?:\.localhost)?\\(?<distribution>[^\\]+)(?<path>\\.*)$'

if ($projectWindowsPath -notmatch $wslUncPattern) {
    throw 'The repository must be opened from its Ubuntu WSL filesystem.'
}

$distributionName = $Matches.distribution
$projectPath = $Matches.path.Replace('\', '/')
$command = "cd '$projectPath' && bash scripts/run_dev.sh"

Write-Host 'Starting AOI Studio inside Ubuntu WSL...'
& wsl.exe -d $distributionName -- bash -lc $command

if ($LASTEXITCODE -ne 0) {
    throw "AOI Studio exited with code $LASTEXITCODE."
}