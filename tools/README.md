Run merge examples and generate reports

## Usage

From the project root run:

```bash
python3 tools/run_merge_examples.py [--build] [--dry-run]
```

### Options

- `--build`: Run `cargo build` before executing merge scenarios
- `--dry-run`: Print commands without executing them

## What the script does

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

## Output structure

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

## Requirements

- **Required**: `git` (for `git merge-file` command)
- **Required**: Python 3 with `rich` library (`pip3 install rich`)
- **Optional**: `mergiraf` and `mergiraf-semi` binaries (script will skip if not found)

## Notes

- The script always overwrites output files to reflect the latest run
- Merge outputs are written as `.swift` files even when merges fail (to preserve conflict markers or partial results)
- Stderr is saved separately in `.stderr` files for diagnostic purposes
- Empty diff files are automatically removed (indicating a MATCH)
