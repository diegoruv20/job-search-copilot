param(
    [switch]$Demo,
    [switch]$SkipTests
)

Write-Host ""
Write-Host "Starting Job Search Copilot setup..." -ForegroundColor Cyan
Write-Host "The installer will explain each step and will not overwrite your profile." -ForegroundColor DarkGray

$arguments = @("scripts\bootstrap.py")
if ($Demo) {
    $arguments += "--demo"
}
if ($SkipTests) {
    $arguments += "--skip-tests"
}

$launcher = Get-Command py -ErrorAction SilentlyContinue
if ($launcher) {
    Write-Host "Using the Windows Python launcher: py -3" -ForegroundColor DarkGray
    & py -3 @arguments
} else {
    Write-Host "The 'py' launcher was not found; trying 'python'." -ForegroundColor Yellow
    & python @arguments
}

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Setup failed. Review the error above, fix it, and run this script again." -ForegroundColor Red
    exit $LASTEXITCODE
}
