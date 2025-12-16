#!/usr/bin/env python3
"""
Run 3-way merges for each scenario under `examples/swift`.
Produces a `report/` folder inside each scenario with merged outputs and diffs against `expected.swift`.
"""

import argparse
import subprocess
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional

from rich import print as rprint
from rich.console import Group
from rich.panel import Panel
from rich.table import Table

# --- Configuration & Constants ---

@dataclass
class Config:
    repo_root: Path
    examples_dir: Path
    dry_run: bool
    build: bool

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> 'Config':
        repo_root = Path(__file__).resolve().parents[1]
        return cls(
            repo_root=repo_root,
            examples_dir=repo_root / "examples" / "swift",
            dry_run=args.dry_run,
            build=args.build
        )

# --- Domain Models ---

class Status(Enum):
    SUCCESS = "SUCCESS"
    CONFLICTS = "CONFLICTS"
    FAILED = "FAILED"
    NO_OUTPUT = "NO_OUTPUT"
    DRY_RUN = "DRY_RUN"

@dataclass
class ToolResult:
    tool_name: str
    status: Status
    exit_code: int
    comparison_status: str  # MATCH, DIFFER, or NO_OUTPUT
    output_file: Path
    logs: List[str] = field(default_factory=list)

@dataclass
class Scenario:
    name: str
    path: Path
    base: Path
    left: Path
    right: Path
    expected: Path
    report_dir: Path
    diffs_dir: Path

    def __post_init__(self):
        self.report_dir = self.path / "report"
        self.diffs_dir = self.report_dir / "diffs"

    @classmethod
    def from_path(cls, path: Path) -> Optional['Scenario']:
        if not path.is_dir():
            return None
        
        # Define expected files
        s = cls(
            name=path.name,
            path=path,
            base=path / "base.swift",
            left=path / "left.swift",
            right=path / "right.swift",
            expected=path / "expected.swift",
            report_dir=path / "report",
            diffs_dir=path / "report" / "diffs"
        )
        
        # Validation
        missing = [f.name for f in (s.base, s.left, s.right, s.expected) if not f.exists()]
        if missing:
            rprint(f"[yellow]Skipping {s.name}: Missing files {missing}[/yellow]")
            return None
            
        return s

    def prepare_dirs(self):
        self.report_dir.mkdir(parents=True, exist_ok=True)
        self.diffs_dir.mkdir(parents=True, exist_ok=True)

class MergeTool:
    def __init__(self, name: str, cmd_template: List[str], accepted_exit_codes: List[int] = None):
        self.name = name
        self.cmd_template = cmd_template
        self.accepted_exit_codes = accepted_exit_codes or [0]

    def run(self, scenario: Scenario, config: Config) -> ToolResult:
        logs = []
        out_path = scenario.report_dir / f"merged_{self.name.replace('-', '_')}.swift"
        stderr_path = scenario.report_dir / f"{out_path.name}.stderr"
        
        # Reset files
        out_path.write_text("")
        stderr_path.write_text("")

        logs.append(f"[cyan]Running: {self.name}[/cyan]")

        if config.dry_run:
            logs.append("  [dim]dry-run: not executing[/dim]")
            return ToolResult(self.name, Status.DRY_RUN, 0, "DRY_RUN", out_path, logs)

        # Execute
        # We run from the scenario directory to ensure tools use relative paths in conflict markers
        try:            
            full_cmd = self.cmd_template + ["base.swift", "left.swift", "right.swift"]
            if self.name == "diff3":
                # Git merge-file order: <current/left> <base> <other/right>
                full_cmd = self.cmd_template + ["left.swift", "base.swift", "right.swift"]

            result = subprocess.run(
                full_cmd,
                cwd=str(scenario.path),
                capture_output=True,
                text=True
            )
            
            # Write output
            out_content = result.stdout or ""
            out_path.write_text(out_content)
            
            if result.stderr:
                stderr_path.write_text(result.stderr)

            # Determine Status
            status = Status.FAILED
            if result.returncode in self.accepted_exit_codes:
                has_markers = any(m in out_content for m in ("<<<<<<<", "|||||||", "=======", ">>>>>>>"))
                if has_markers:
                    logs.append(f"  [yellow]⚠ {self.name} exit {result.returncode} (conflicts present)[/yellow]")
                    status = Status.CONFLICTS
                else:
                    logs.append(f"  [green]✓ {self.name} exit: {result.returncode}[/green]")
                    status = Status.SUCCESS
            else:
                logs.append(f"  [red]✗ failed (exit {result.returncode}), see {stderr_path.name}[/red]")
                status = Status.FAILED

        except FileNotFoundError:
            logs.append(f"  [red]Executable not found for {self.name}[/red]")
            return ToolResult(self.name, Status.FAILED, -1, "ERR", out_path, logs)

        # Compare vs Expected
        comp_status = self._compare(scenario, out_path, logs, config)
        
        return ToolResult(self.name, status, result.returncode, comp_status, out_path, logs)

    def _compare(self, scenario: Scenario, merged_path: Path, logs: List[str], config: Config) -> str:
        tag = f"{self.name}_vs_expected"
        diff_path = scenario.diffs_dir / f"{tag}.diff"
        
        if config.dry_run:
            return "DRY_RUN"
            
        if not merged_path.exists() or merged_path.stat().st_size == 0:
            logs.append(f"  [dim]{tag}: no output produced[/dim]")
            return "DIFFER"

        # Run diff
        cmd = ["diff", "-u", str(scenario.expected.name), str(merged_path.name)]
        # We run diff from inside report dir or using absolute paths? 
        # Using absolute paths is safer.
        cmd = ["diff", "-u", str(scenario.expected), str(merged_path)]
        
        r = subprocess.run(cmd, capture_output=True, text=True)
        diff_path.write_text(r.stdout or "")
        
        if diff_path.stat().st_size > 0:
            logs.append(f"  [red]✗ {tag}: DIFFER (see {diff_path.name})[/red]")
            return "DIFFER"
        else:
            logs.append(f"  [green]✓ {tag}: MATCH[/green]")
            diff_path.unlink(missing_ok=True)
            return "MATCH"

# --- Infrastructure Functions ---

def run_build(config: Config):
    """Builds the project using cargo if requested."""
    cargo_toml = config.repo_root / "Cargo.toml"
    if not cargo_toml.exists():
        rprint(f"[yellow]Cargo.toml not found at {config.repo_root}. Skipping build.[/yellow]")
        return

    rprint("[cyan]Building mergiraf via `cargo build`...[/cyan]")
    if not config.dry_run:
        r = subprocess.run(["cargo", "build"], cwd=str(config.repo_root))
        if r.returncode != 0:
            rprint("[yellow]cargo build failed; continuing but merges may fail.[/yellow]")
            sys.exit(1)
    else:
        rprint("[dim]Dry run: cargo build skipped[/dim]")

def display_scenario_result(scenario: Scenario, results: List[ToolResult]):
    """Renders the results of a single scenario to the terminal using Rich."""
    log_content = []
    
    # Aggregate logs
    for res in results:
        log_content.extend(res.logs)
    
    # Create Summary Table
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Tool", style="cyan")
    table.add_column("Status")
    table.add_column("Comparison")
    table.add_column("Output File", style="dim")

    for res in results:
        # Style the status
        status_style = "green" if res.status == Status.SUCCESS else "yellow" if res.status == Status.CONFLICTS else "red"
        status_text = f"{res.status.value} ({res.exit_code})"
        
        # Style the comparison
        comp_style = "green" if res.comparison_status == "MATCH" else "red"
        
        table.add_row(
            res.tool_name, 
            f"[{status_style}]{status_text}[/{status_style}]", 
            f"[{comp_style}]{res.comparison_status}[/{comp_style}]",
            res.output_file.name
        )

    log_content.append("")
    log_content.append(f"[dim]Report saved to: {scenario.report_dir}[/dim]")
    
    # Group logs and table
    content = Group("\n".join(log_content), "", table)
    rprint(Panel(content, title=f"[bold]Scenario: {scenario.name}[/bold]", border_style="cyan"))

# --- Main Execution Flow ---

def main():
    parser = argparse.ArgumentParser(description="Run merge examples and generate reports")
    parser.add_argument("--build", action="store_true", help="Run `cargo build` at repo root before runs")
    parser.add_argument("--dry-run", action="store_true", help="Don't execute commands; just print what would run")
    args = parser.parse_args()

    config = Config.from_args(args)

    if not config.examples_dir.is_dir():
        rprint(f"[red]Examples directory not found: {config.examples_dir}[/red]")
        sys.exit(1)

    if config.build:
        run_build(config)

    rprint(f"[bold green]Running merge examples in: {config.examples_dir}[/bold green]")

    # Define Tools
    # Note: `mergiraf` accepts 0 (clean) and 1 (conflict) as valid exit codes
    tools = [
        MergeTool("diff3", ["git", "merge-file", "-p"], accepted_exit_codes=[0, 1]),
        MergeTool("mergiraf-semi", ["cargo", "run", "--quiet", "--", "merge", "--semistructured=diff3"], accepted_exit_codes=[0, 1]),
        MergeTool("mergiraf", [f"{config.repo_root}/target/debug/mergiraf", "merge"], accepted_exit_codes=[0, 1]),
    ]

    scenarios_path = sorted(config.examples_dir.iterdir())
    
    for dir_path in scenarios_path:
        scenario = Scenario.from_path(dir_path)
        if not scenario:
            continue

        scenario.prepare_dirs()
        
        results = []
        for tool in tools:
            results.append(tool.run(scenario, config))
            
        display_scenario_result(scenario, results)

if __name__ == "__main__":
    main()