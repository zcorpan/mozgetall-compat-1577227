#!/bin/sh
# Before (A), before again (A2), after (B), with the pref build. Usage: compare_run.sh FIREFOX PAGES OUTDIR
set -e
.venv/bin/python scripts/harness.py "$1" on "$2" "$3/a.jsonl" 4 --screenshots
.venv/bin/python scripts/harness.py "$1" on "$2" "$3/a2.jsonl" 4 --screenshots
.venv/bin/python scripts/harness.py "$1" off "$2" "$3/b.jsonl" 4 --screenshots
