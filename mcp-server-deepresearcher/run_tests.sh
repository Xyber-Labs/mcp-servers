#!/bin/bash
# Run tests excluding e2e tests by default
# Usage: ./run_tests.sh [pytest args...]

cd "$(dirname "$0")"

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Run tests excluding e2e directory and integration/slow markers
# Pass any additional arguments to pytest
pytest tests/ \
    --ignore=tests/e2e \
    -m "not integration and not slow" \
    -v \
    "$@"

