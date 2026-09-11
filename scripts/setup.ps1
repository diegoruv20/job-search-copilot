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

python @arguments
