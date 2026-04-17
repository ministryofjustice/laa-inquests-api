#!/bin/bash
set +e

echo "Adding Branch name to commit"
msg_file="$1"
branch=$(git rev-parse --abbrev-ref HEAD)

if [ "$branch" == "HEAD" ]; then
  # Detached HEAD, likely during a merge or rebase; do not modify commit message
  exit 0
fi

echo "$branch" | grep -Eo '^dependabot'

if [ $? -eq 0 ]; then
  exit 0
fi

ticket=$(echo "$branch" | grep -Eo 'IDDS-[0-9]+')

if [ $? -ne 0 ]; then
  echo "Branch name does not match expected pattern IDDS-XXX"
  exit 1
fi

if [ -z "$ticket" ]; then
  echo "Could not determine ticket from branch name"
  exit 1
fi
msg=$(cat "${msg_file}")

# Remove the ticket prefix if one already exists in the commit message
msg=$(echo "${msg}" | sed "s/^\[IDDS-[0-9]\+\] *//")

echo "[${ticket}] ${msg}" > "${msg_file}"