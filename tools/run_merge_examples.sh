#!/usr/bin/env bash
set -euo pipefail

# Run 3-way merges for each scenario under mergiraf-semi/examples/swift
# Produces a `report/` folder inside each scenario with merged outputs and diffs against `expected.swift`.

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
examples_dir="$repo_root/examples/swift"

if [ ! -d "$examples_dir" ]; then
  echo "Examples directory not found: $examples_dir"
  exit 1
fi

echo "  - Checking for mergiraf binaries "
  # Build the project if the bash receives a --build flag
  if [[ " $@ " =~ " --build " ]]; then
    if [ ! -f "$repo_root/Cargo.toml" ]; then
      echo "  - Cargo.toml not found in repo root: $repo_root"
      echo "    Skipping experiment."
      continue
    fi
    echo "  - Building mergiraf ..."
    (cd "$repo_root" && cargo build)
  fi

echo "Running merge examples in: $examples_dir"

for dir in "$examples_dir"/*; do
  [ -d "$dir" ] || continue
  scenario="$(basename "$dir")"
  echo "\n=========== Scenario: $scenario ==========="

  base="$dir/base.swift"
  left="$dir/left.swift"
  right="$dir/right.swift"
  expected="$dir/expected.swift"
  report_dir="$dir/report"

  # Reset report directory for this scenario 
  rm -rf "$report_dir"
  mkdir -p "$report_dir/diffs"

  # Check that all required files exist
  missing=0
  for f in "$base" "$left" "$right" "$expected"; do
    if [ ! -f "$f" ]; then
      echo "  - missing file: $f"
      missing=1
    fi
  done
  if [ "$missing" -ne 0 ]; then
    echo "  Skipping scenario due to missing files."
    continue
  fi

  # 1) Line-based merge using git merge-file (diff3 style)
  out_diff3="$report_dir/merged_diff3.swift"
  stderr_diff3="$report_dir/merged_diff3.stderr"

  echo "  - Running diff3 (git merge-file) ..."
  if git merge-file -p "$left" "$base" "$right" > "$out_diff3" 2> "$stderr_diff3"; then
    echo "    -> diff3 exit: 0 (no conflicts)"
  else
    rc=$?
    # write a short header into the output file so it always reflects the last run
    printf '// diff3 (git merge-file) failed with exit %d. See %s\n' "$rc" "$stderr_diff3" > "$out_diff3"
    echo "    -> diff3 exit: non-zero (conflicts or merge markers), see $stderr_diff3"
  fi

  echo "  - Running mergers ..."

  # 2) Try running mergiraf (if available)
  run_tool() {
    local cmd_path="$1"
    local out_file="$2"
    local stderr_file="$report_dir/$(basename "$out_file").stderr"    

    # Use eval because cmd_path may contain a compound command (cd && ./bin)
    local exec_cmd="${cmd_path} $left $base $right > '$out_file' 2> '$stderr_file'"
    if eval "$exec_cmd"; then
      echo "       Exit: 0 (success)"
      return 0
    else
      rc=$?
      # Write a helpful header into the output file so it reflects the failure
      printf '// %s failed with exit %d. See %s\n' "$(basename "$cmd_path")" "$rc" "$stderr_file" > "$out_file"
      echo "       Exit: non-zero (errors), see $stderr_file"
      return $rc
    fi
  }

  echo "  - Running mergers ..."

  # mergiraf runner
  mergiraf_cmd="cd $repo_root/target/debug && ./mergiraf merge"
  mergiraf_out="$report_dir/merged_mergiraf.swift"
  run_tool "$mergiraf_cmd" "$mergiraf_out"

  # mergiraf-semi runner
  mergiraf_semi_cmd="cargo run -- merge --semistructured=diff3"
  mergiraf_semi_out="$report_dir/merged_mergiraf_semi.swift"
  run_tool "$mergiraf_semi_cmd" "$mergiraf_semi_out"

  # 3) Compare each merged output to expected
  compare_and_save() {
    local merged="$1"
    local tag="$2"
    if [ -f "$merged" ]; then
      diff -u "$expected" "$merged" > "$report_dir/diffs/${tag}.diff" || true
      if [ -s "$report_dir/diffs/${tag}.diff" ]; then
        echo "  - $tag: DIFFER (see $report_dir/diffs/${tag}.diff)"
      else
        echo "  - $tag: MATCH"
        rm -f "$report_dir/diffs/${tag}.diff"
      fi
    else
      echo "  - $tag: no output produced"
    fi
  }

  compare_and_save "$out_diff3" "diff3_vs_expected"
  compare_and_save "$mergiraf_out" "mergiraf_vs_expected"
  compare_and_save "$mergiraf_semi_out" "mergiraf-semi_vs_expected"

  echo "  Report saved to: $report_dir"
done

echo "\nDone. Check each scenario's report folder for merged outputs and diffs."
