#!/bin/bash
set -euo pipefail

# Reads the migration scripts on disk only (no database connection) and fails
# if the revision tree has branched into more than one head.
head_count=$(alembic heads | grep -c '(head)')

if [ "$head_count" -gt 1 ]; then
  echo "Multiple Alembic migration heads detected (${head_count}):"
  echo ""
  alembic heads
  echo ""
  echo "Two migrations share the same down_revision"
  exit 1
fi

echo "Single Alembic migration head - no branch conflict."
