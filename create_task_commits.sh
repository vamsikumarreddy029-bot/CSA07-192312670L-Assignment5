#!/usr/bin/env bash
set -euo pipefail
# Run once after creating the GitHub repository and reviewing all files.
# This creates one local commit per task folder, as required by the brief.
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git init
fi
for task in Task01 Task02 Task03 Task04 Task05 Task06 Task07 Task08 Task09; do
  git add "$task"
  git commit -m "Complete ${task} deliverables"
done
git add README.md ANSWERS_AND_ANALYSIS.md run_all.py configs evidence create_task_commits.sh
# Add the shared runner/evidence as a final integration commit.
git commit -m "Add reproducible experiment runner and evidence"
echo "Add your GitHub remote, then run: git push -u origin main"
