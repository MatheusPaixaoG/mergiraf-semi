# Merge Tools Testing Scripts

This directory contains Python scripts for testing and analyzing merge tool performance on Swift code examples.

## Scripts

### 1. run_merge_examples.py

Runs merge tools on all Swift scenarios and generates detailed reports.

#### Usage

From the project root run:

```bash
python3 tools/run_merge_examples.py [--build] [--dry-run]
```

#### Options

- `--build`: Run `cargo build` before executing merge scenarios
- `--dry-run`: Print commands without executing them

#### What the script does

For each scenario folder under `examples/swift/`:

1. **Runs diff3 merge**: Executes `git merge-file -p left base right` and saves output to `report/merged_diff3.swift`
   - On success: writes clean merge output
   - On conflicts: writes merge output with conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`)

2. **Runs mergiraf**: Attempts to run `mergiraf merge` (checks `target/debug/mergiraf`, PATH, or `cargo run`)
   - Saves output to `report/merged_mergiraf.swift`
   - Skips if binary not found

3. **Runs mergiraf-semi**: Attempts to run `mergiraf merge --semistructured=diff3` 
   - Saves output to `report/merged_mergiraf_semi.swift`
   - Skips if binary not found

4. **Compares results**: Diffs each merged output against `expected.swift`
   - Stores diffs in `report/diffs/` (only if outputs differ)
   - Reports MATCH/DIFFER status for each tool

5. **Displays results**: Uses Rich library to show formatted panels with:
   - Execution logs for each step
   - Summary table with run status and compare results
   - Color-coded output (green ✓ for success, yellow ⚠ for conflicts, red ✗ for failures)

6. **Generates confusion matrices**: Displays TP, TN, FP, FN, and error counts for each tool by reading from `scenarios.json`

#### Output structure

Each scenario creates:
```
examples/swift/<scenario>/
├── report/
│   ├── merged_diff3.swift          # diff3 merge output
│   ├── merged_diff3.swift.stderr   # stderr if any
│   ├── merged_mergiraf.swift       # mergiraf output
│   ├── merged_mergiraf.swift.stderr
│   ├── merged_mergiraf_semi.swift  # mergiraf-semi output
│   ├── merged_mergiraf_semi.swift.stderr
│   └── diffs/
│       ├── diff3_vs_expected.diff       # only if differs
│       ├── mergiraf_vs_expected.diff
│       └── mergiraf-semi_vs_expected.diff
```

---

### 2. compute_comparison_metrics.py

Analyzes results from `scenarios.json` and computes pairwise comparison metrics between merge tools.

#### Usage

From the project root run:

```bash
python3 tools/compute_comparison_metrics.py [--debug]
```

#### Options

- `--debug`: Enable detailed debug output showing scenario-by-scenario analysis and divergence detection

#### What the script does

1. **Reads scenarios.json**: Loads expected results and actual tool outputs for all scenarios
2. **Generates confusion matrices**: Displays TP (True Positive), TN (True Negative), FP (False Positive), FN (False Negative), and error counts for each tool
3. **Computes pairwise comparisons**: Analyzes tool pairs (e.g., diff3 vs mergiraf) to calculate:
   - **aTP** (Additional True Positives): Cases where tool A correctly detected a conflict but tool B didn't
   - **aTN** (Additional True Negatives): Cases where tool A correctly merged but tool B didn't
   - **aFP** (Additional False Positives): Cases where tool A incorrectly reported a conflict but tool B was correct
   - **aFN** (Additional False Negatives): Cases where tool A missed a conflict but tool B detected it
4. **Displays detailed tables**: Shows metric counts and the specific scenarios contributing to each metric

#### Output

- **Without --debug**: Shows only summary tables with confusion matrices and comparison metrics
- **With --debug**: Includes detailed messages for each scenario showing:
  - When tools produce different results
  - Which tool produced the expected output
  - Execution status and comparison results for each divergence

---

## Requirements

- **Required**: `git` (for `git merge-file` command)
- **Required**: Python 3.7+ with `rich` library (`pip install rich`)
- **Optional**: `mergiraf` and `mergiraf-semi` binaries (run_merge_examples.py will skip if not found)

## scenarios.json Format

The `examples/swift/scenarios.json` file is a manually created ground truth file that contains expected results and tool execution outcomes. This file should be populated based on the output provided by `run_merge_examples.py` after running the scenarios.

Format:

```json
{
  "scenario_name": {
    "expected": "CONFLICT" or "SUCCESS",
    "diff3": {
      "execution": "SUCCESS" | "CONFLICTS (exit N)" | "FAILED (exit N)",
      "comparison": "MATCH" | "DIFFER"
    },
    "mergiraf": { ... },
    "mergiraf-semi": { ... }
  }
}
```

## Workflow

1. **Run scenarios**: `python3 tools/run_merge_examples.py --build`
2. **Analyze results**: `python3 tools/compute_comparison_metrics.py`
3. **Debug issues**: `python3 tools/compute_comparison_metrics.py --debug`

## Notes

- The scripts always overwrite output files to reflect the latest run
- Merge outputs are written as `.swift` files even when merges fail (to preserve conflict markers or partial results)
- Stderr is saved separately in `.stderr` files for diagnostic purposes
- Empty diff files are automatically removed (indicating a MATCH)
- Conflict markers use relative filenames (e.g., `left.swift`) instead of full paths
