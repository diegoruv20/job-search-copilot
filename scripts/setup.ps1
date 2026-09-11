param(
    [switch]$Demo,
    [switch]$SkipTests
)

$arguments = @("scripts\bootstrap.py")
if ($Demo) {
    $arguments += "--demo"
}
if ($SkipTests) {
    $arguments += "--skip-tests"
}

$launcher = Get-Command py -ErrorAction SilentlyContinue
if ($launcher) {
    & py -3 @arguments
} else {
    & python @arguments
}
