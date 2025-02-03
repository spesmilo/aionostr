#!/bin/bash

set -e

PROJECT_ROOT="$(dirname "$(readlink -e "$0")")/.."
CONTRIB="$PROJECT_ROOT/contrib"

cd "$PROJECT_ROOT"


git_status=$(git status --porcelain)
if [ ! -z "$git_status" ]; then
    echo "$git_status"
    echo "git repo not clean, aborting"
    exit 1
fi


cd "$PROJECT_ROOT"
python3 -m build --sdist .

