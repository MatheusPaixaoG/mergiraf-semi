Run merge examples and generate reports

Usage

- From the project root run:

  ```bash
  bash tools/run_merge_examples.sh
  ```

What the script does

- Iterates each scenario folder under `mergiraf-semi/examples/swift`.
- Runs a line-based 3-way merge (`git merge-file -p left base right`) and saves output to `report/merged.diff3.swift`.
- If available, attempts to run `mergiraf` / `mergiraf-semi` binaries (checks PATH and `mergiraf-semi/target/debug`).
- Compares each merged output with `expected.swift` and stores diffs under `report/diffs/`.

Notes

- `git merge-file` must be available (part of git) for the diff3-style merges.
- `mergiraf` and `mergiraf-semi` are optional; the script performs best-effort invocations and will skip them if not found.
- You can inspect each scenario's `report/` folder for merged outputs and the `diffs/` subfolder for differences vs. `expected.swift`.
