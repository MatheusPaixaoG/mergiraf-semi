#!/usr/bin/env python3
"""
Run 3-way merges for each scenario under `examples/swift`.
Produces a `report/` folder inside each scenario with merged outputs and diffs against `expected.swift`.

This is a near-direct rewrite of the previous Bash runner with the following improvements:
- Always truncates/overwrites merged output and stderr files so they reflect the latest run.
- Writes a short header into merged output files when a tool fails or is missing.
- Supports `--build` to run `cargo build` before running merges.
- Supports `--dry-run` to print actions without executing them.
"""

import argparse
import subprocess
import sys
from pathlib import Path

from rich import print as rprint
from rich.table import Table
from rich.panel import Panel

def run(cmd, *, shell=False, capture_stdout=False, capture_stderr=False):
    return subprocess.run(cmd, shell=shell, stdout=subprocess.PIPE if capture_stdout else None,
                          stderr=subprocess.PIPE if capture_stderr else None, text=True)


def truncate(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("")


def write_header(path: Path, message: str):
    path.write_text(f"// {message}\n")

def main(argv=None):
    parser = argparse.ArgumentParser(description="Run merge examples and generate reports")
    parser.add_argument("--build", action="store_true", help="Run `cargo build` at repo root before runs")
    parser.add_argument("--dry-run", action="store_true", help="Don't execute commands; just print what would run")
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parents[1]
    examples_dir = repo_root / "examples" / "swift"

    if not examples_dir.is_dir():
        rprint(f"[red]Examples directory not found: {examples_dir}[/red]")
        sys.exit(1)

    if args.build:
        cargo_toml = repo_root / "Cargo.toml"
        if not cargo_toml.exists():
            rprint(f"[yellow]Cargo.toml not found in repo root: {repo_root}. Skipping build.[/yellow]")
        else:
            rprint("[cyan]Building mergiraf via `cargo build`...[/cyan]")
            if not args.dry_run:
                r = run(["cargo", "build"], shell=False)
                if r.returncode != 0:
                    rprint("[yellow]cargo build failed; continuing but merges may fail.[/yellow]")
                    sys.exit(1)

    rprint(f"[bold green]Running merge examples in: {examples_dir}[/bold green]")

    for dir_path in sorted(examples_dir.iterdir()):
        if not dir_path.is_dir():
            continue
        scenario = dir_path.name
        
        # Collect all output for this scenario
        log = []

        base = dir_path / "base.swift"
        left = dir_path / "left.swift"
        right = dir_path / "right.swift"
        expected = dir_path / "expected.swift"
        report_dir = dir_path / "report"
        diffs_dir = report_dir / "diffs"

        report_dir.mkdir(parents=True, exist_ok=True)
        diffs_dir.mkdir(parents=True, exist_ok=True)

        missing = False
        for p in (base, left, right, expected):
            if not p.exists():
                log.append(f"[red]Missing file: {p}[/red]")
                missing = True
        if missing:
            log.append("[yellow]Skipping scenario due to missing files.[/yellow]")
            rprint(Panel("\n".join(log), title=f"Scenario: {scenario}", border_style="yellow"))
            continue

        # 2) Try running mergiraf / mergiraf-semi
        def run_tool(cmd_template: str, out_path: Path):
            stderr_path = report_dir / (out_path.name + ".stderr")
            truncate(out_path)
            truncate(stderr_path)

            # Append the left/base/right order similar to the original script
            full_cmd = f"{cmd_template} {base} {left} {right}"
            if args.dry_run:
                log.append("  [dim]dry-run: not executing[/dim]")
                return None

            # Run with shell=True because cmd_template may include cd/&&
            r = subprocess.run(full_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            return r

        # 3) Compare each merged output to expected
        def compare_and_save(merged: Path, tag: str):
            diff_path = diffs_dir / f"{tag}.diff"
            if not merged.exists():
                log.append(f"  [dim]{tag}: no output produced[/dim]")
                return "NO_OUTPUT"
            cmd = ["diff", "-u", str(expected), str(merged)]
            if args.dry_run:
                log.append(f"  [dim]dry-run: {' '.join(cmd)}[/dim]")
                return "DRY_RUN"
            r = run(cmd, shell=False, capture_stdout=True, capture_stderr=True)
            # write diff output even if empty to represent this run
            diff_path.write_text(r.stdout or "")
            if diff_path.stat().st_size > 0:
                log.append(f"  [red]✗ {tag}: DIFFER (see {diff_path.name})[/red]")
                return "DIFFER"
            else:
                log.append(f"  [green]✓ {tag}: MATCH[/green]")
                diff_path.unlink()
                return "MATCH"

        # 1) Line-based merge using git merge-file (diff3 style)
        out_diff3 = report_dir / "merged_diff3.swift"
        stderr_diff3 = report_dir / "merged_diff3.stderr"
        truncate(out_diff3)
        truncate(stderr_diff3)

        log.append("[cyan]Running diff3 (git merge-file)...[/cyan]")
        cmd = ["git", "merge-file", "-p", str(left), str(base), str(right)]
        if args.dry_run:
            log.append(f"  [dim]dry-run: {' '.join(cmd)}[/dim]")
            diff3_status = "DRY_RUN"
        else:
            r = run(cmd, shell=False, capture_stdout=True, capture_stderr=True)
            if r.returncode == 0:
                out_diff3.write_text(r.stdout or "")
                log.append("  [green]✓ diff3 exit: 0 (no conflicts)[/green]")
                diff3_status = "SUCCESS"
            else:
                # git merge-file outputs merged result with conflict markers to stdout even on failure
                out_diff3.write_text(r.stdout or "")
                # save stderr separately if there are any error messages
                if r.stderr:
                    stderr_diff3.write_text(r.stderr)
                log.append(f"  [yellow]⚠ diff3 exit: {r.returncode} (conflicts in output)[/yellow]")
                diff3_status = f"CONFLICTS (exit {r.returncode})"

        diff3_compare = compare_and_save(out_diff3, "diff3_vs_expected")

        # Candidate commands (some may be compound commands)
        candidates_mergiraf = [
            f"{repo_root}/target/debug/mergiraf merge",
            f"{repo_root}/target/debug/mergiraf",
            "mergiraf"
        ]

        candidates_mergiraf_semi = [
            "cargo run -- merge --semistructured=diff3"
        ]

        mergiraf_out = report_dir / "merged_mergiraf.swift"
        mergiraf_semi_out = report_dir / "merged_mergiraf_semi.swift"

        # Try candidates for mergiraf (stop at first success)
        mergiraf_status = "NO_OUTPUT"
        for c in candidates_mergiraf:
            log.append(f"[cyan]Running: mergiraf[/cyan]")
            r = run_tool(c, mergiraf_out)
            stderr_path = report_dir / (mergiraf_out.name + ".stderr")
            if r.returncode == 0:
                if any(marker in r.stdout for marker in ("<<<<<<<", "|||||||", "=======", ">>>>>>>")):
                    # Write stdout (may contain merge output with conflicts) to .swift file
                    mergiraf_out.write_text(r.stdout or "")
                    log.append(f"  [yellow]⚠ mergiraf exit {r.returncode} (check output for conflicts)[/yellow]")
                    mergiraf_status = f"CONFLICTS (exit {r.returncode})"
                    break
                else:
                    mergiraf_out.write_text(r.stdout or "")
                    log.append("  [green]✓ mergiraf exit: 0 (no conflicts)[/green]")
                    mergiraf_status = "SUCCESS"
                    break
            elif r.returncode is None:
                mergiraf_status = "DRY_RUN"
            else:
                # Write stdout (may contain merge output with conflicts) to .swift file
                mergiraf_out.write_text(r.stdout or "")
                # Save stderr separately if there are error messages
                if r.stderr:
                    stderr_path.write_text(r.stderr)
                    log.append(f"  [red]✗ failed (exit {r.returncode}), see {stderr_path.name}[/red]")
                else:
                    log.append(f"  [yellow]⚠ exit {r.returncode} (check output for conflicts)[/yellow]")
                mergiraf_status = f"FAILED (exit {r.returncode})"
        
        if mergiraf_status.startswith("FAILED") or mergiraf_status == "NO_OUTPUT":
            log.append("[yellow]mergiraf: not found or invocation failed, skipping.[/yellow]")

        mergiraf_compare = compare_and_save(mergiraf_out, "mergiraf_vs_expected")

        # Try candidates for mergiraf-semi (stop at first success)
        mergiraf_semi_status = "NO_OUTPUT"
        for c in candidates_mergiraf_semi:
            log.append(f"[cyan]Running: mergiraf-semi[/cyan]")
            r = run_tool(c, mergiraf_semi_out)
            stderr_path = report_dir / (mergiraf_semi_out.name + ".stderr")
            if r.returncode == 0:
                if any(marker in r.stdout for marker in ("<<<<<<<", "|||||||", "=======", ">>>>>>>")):
                    # Write stdout (may contain merge output with conflicts) to .swift file
                    mergiraf_semi_out.write_text(r.stdout or "")
                    log.append(f"  [yellow]⚠ mergiraf-semi exit {r.returncode} (check output for conflicts)[/yellow]")
                    mergiraf_semi_status = f"CONFLICTS (exit {r.returncode})"
                    break
                else:
                    mergiraf_semi_out.write_text(r.stdout or "")
                    log.append("  [green]✓ mergiraf-semi exit: 0 (no conflicts)[/green]")
                    mergiraf_semi_status = "SUCCESS"
                    break
            elif r.returncode is None:
                mergiraf_semi_status = "DRY_RUN"
            else:
                # Write stdout (may contain merge output with conflicts) to .swift file
                mergiraf_semi_out.write_text(r.stdout or "")
                # Save stderr separately if there are error messages
                if r.stderr:
                    stderr_path.write_text(r.stderr)
                    log.append(f"  [red]✗ failed (exit {r.returncode}), see {stderr_path.name}[/red]")
                else:
                    log.append(f"  [yellow]⚠ exit {r.returncode} (check output for conflicts)[/yellow]")
                mergiraf_semi_status = f"FAILED (exit {r.returncode})"

        if mergiraf_semi_status.startswith("FAILED") or mergiraf_semi_status == "NO_OUTPUT":
            log.append("[yellow]mergiraf-semi: not found or invocation failed, skipping.[/yellow]")

        mergiraf_semi_compare = compare_and_save(mergiraf_semi_out, "mergiraf-semi_vs_expected")

        # Add summary table
        log.append("")
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Tool")
        table.add_column("Run Status")
        table.add_column("Compare")
        table.add_column("Output File")

        table.add_row("diff3", diff3_status, diff3_compare, str(out_diff3.name))
        table.add_row("mergiraf", mergiraf_status, mergiraf_compare, str(mergiraf_out.name))
        table.add_row("mergiraf-semi", mergiraf_semi_status, mergiraf_semi_compare, str(mergiraf_semi_out.name))

        log.append(f"[dim]Report saved to: {report_dir}[/dim]")

        # Render single panel with all scenario output
        from rich.console import Group
        content = Group("\n".join(log), "", table)
        rprint(Panel(content, title=f"[bold]Scenario: {scenario}[/bold]", border_style="cyan"))

    rprint("\n[bold green]Done. Check each scenario's report folder for merged outputs and diffs.[/bold green]")


if __name__ == "__main__":
    main()
