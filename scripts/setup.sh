#!/usr/bin/env sh
set -eu

printf "\nStarting Job Search Copilot setup...\n"
printf "The installer will explain each step and preserve existing profile files.\n"
printf "Using Python launcher: python3\n\n"

python3 scripts/bootstrap.py "$@"
