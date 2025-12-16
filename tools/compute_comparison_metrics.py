#!/usr/bin/env python3
"""
Compute Comparison Metrics for Merge Tools
"""

import argparse
import json
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Tuple

from rich import print as rprint
from rich.panel import Panel
from rich.table import Table

# --- Enums & Constants ---

class ExecutionStatus(str, Enum):
    SUCCESS = "SUCCESS"
    CONFLICT = "CONFLICT"
    FAILED = "FAILED"
    NO_OUTPUT = "NO_OUTPUT"
    UNKNOWN = "UNKNOWN_EXECUTION"

class ComparisonStatus(str, Enum):
    MATCH = "MATCH"
    DIFFER = "DIFFER"
    NO_OUTPUT = "NO_OUTPUT"

# --- Data Models ---

@dataclass
class MetricBucket:
    """Holds counts and scenario names for a specific metric."""
    count: int = 0
    scenarios: List[str] = field(default_factory=list)

    def add(self, scenario_name: str):
        self.count += 1
        self.scenarios.append(scenario_name)

    @property
    def scenario_str(self) -> str:
        return ", ".join(self.scenarios) if self.scenarios else "-"

@dataclass
class ToolScenarioResult:
    execution: ExecutionStatus
    comparison: ComparisonStatus

@dataclass
class SingleToolPairwiseStats:
    """Holds the aTP, aTN, aFP, aFN stats for one tool in a specific pairing."""
    atp: MetricBucket = field(default_factory=MetricBucket)
    atn: MetricBucket = field(default_factory=MetricBucket)
    afp: MetricBucket = field(default_factory=MetricBucket)
    afn: MetricBucket = field(default_factory=MetricBucket)

    def add(self, metric_type: str, scenario: str):
        if metric_type == "aTP": self.atp.add(scenario)
        elif metric_type == "aTN": self.atn.add(scenario)
        elif metric_type == "aFP": self.afp.add(scenario)
        elif metric_type == "aFN": self.afn.add(scenario)

@dataclass
class PairwiseResult:
    """Results of comparing Tool A vs Tool B."""
    tool_a_name: str
    tool_b_name: str
    stats_a: SingleToolPairwiseStats = field(default_factory=SingleToolPairwiseStats)
    stats_b: SingleToolPairwiseStats = field(default_factory=SingleToolPairwiseStats)

# --- Logic ---

class StatisticsCalculator:
    @staticmethod
    def compute_confusion_matrix(tool_name: str, results: Dict[str, ToolScenarioResult]):
        # Re-using the simplified logic for the basic confusion matrix
        # (Since the user only asked to revert the Pairwise logic)
        tp, tn, fp, fn, error = (MetricBucket() for _ in range(5))
        
        for scenario, res in results.items():
            if res.execution in (ExecutionStatus.FAILED, ExecutionStatus.NO_OUTPUT, ExecutionStatus.UNKNOWN):
                error.add(scenario)
                continue

            is_merge = (res.execution == ExecutionStatus.SUCCESS)
            is_correct = (res.comparison == ComparisonStatus.MATCH)

            if is_merge:
                if is_correct: tn.add(scenario)
                else: fn.add(scenario)
            else:
                if is_correct: tp.add(scenario)
                else: fp.add(scenario)
                    
        return {"TP": tp, "TN": tn, "FP": fp, "FN": fn, "error": error}

class PairwiseComparator:
    def __init__(self, data: Dict[str, Dict[str, ToolScenarioResult]], expected_map: Dict[str, str], debug: bool = False):
        self.data = data
        self.expected_map = expected_map
        self.debug = debug

    def compare(self, tool_a: str, tool_b: str) -> PairwiseResult:
        result = PairwiseResult(tool_a, tool_b)
        
        # Get all scenarios present in the expected map
        scenarios = self.expected_map.keys()

        for scenario in scenarios:
            # Defaults
            res_a = self.data[tool_a].get(scenario, ToolScenarioResult(ExecutionStatus.UNKNOWN, ComparisonStatus.NO_OUTPUT))
            res_b = self.data[tool_b].get(scenario, ToolScenarioResult(ExecutionStatus.UNKNOWN, ComparisonStatus.NO_OUTPUT))

            exec_a, comp_a = res_a.execution, res_a.comparison
            exec_b, comp_b = res_b.execution, res_b.comparison

            # --- Logic from original compute_comparison_metrics ---

            # 1. A fails, B succeeds
            if exec_a == ExecutionStatus.FAILED and exec_b != ExecutionStatus.FAILED:
                if comp_b == ComparisonStatus.MATCH:
                    if self.debug:
                        rprint(f"[green]{tool_b} succeeded where {tool_a} failed: {scenario}.[/green]")
                    metric = "aTN" if exec_b == ExecutionStatus.SUCCESS else "aTP"
                    result.stats_b.add(metric, scenario)
                else:
                    if self.debug:
                        rprint(f"[yellow]{tool_b} succeeded where {tool_a} failed, but wrong output: {scenario}.[/yellow]")
                continue

            # 2. B fails, A succeeds
            if exec_b == ExecutionStatus.FAILED and exec_a != ExecutionStatus.FAILED:
                if comp_a == ComparisonStatus.MATCH:
                    if self.debug:
                        rprint(f"[green]{tool_a} succeeded where {tool_b} failed: {scenario}.[/green]")
                    metric = "aTN" if exec_a == ExecutionStatus.SUCCESS else "aTP"
                    result.stats_a.add(metric, scenario)
                else:
                    if self.debug:
                        rprint(f"[yellow]{tool_a} succeeded where {tool_b} failed, but wrong output: {scenario}.[/yellow]")
                continue

            # 3. Same Execution Status
            if exec_a == exec_b:
                # Same outcome (both MATCH or both DIFFER) -> Skip
                if comp_a == comp_b:
                    if self.debug:
                        rprint(f"[yellow]Both tools same result for {scenario}.[/yellow]")
                    continue

                # Divergence
                if self.debug:
                    self._print_divergence(scenario, tool_a, res_a, tool_b, res_b)

                if comp_a == ComparisonStatus.MATCH:
                    # A is correct
                    metric_a = "aTN" if exec_a == ExecutionStatus.SUCCESS else "aTP"
                    metric_b = "aFN" if exec_b == ExecutionStatus.SUCCESS else "aFP"
                    result.stats_a.add(metric_a, scenario)
                    result.stats_b.add(metric_b, scenario)
                else:
                    # B is correct
                    metric_b = "aTN" if exec_b == ExecutionStatus.SUCCESS else "aTP"
                    metric_a = "aFN" if exec_a == ExecutionStatus.SUCCESS else "aFP"
                    result.stats_b.add(metric_b, scenario)
                    result.stats_a.add(metric_a, scenario)
            
            # 4. Different Execution Status (e.g. one Merged, one Conflict)
            else:
                if self.debug:
                    self._print_divergence(scenario, tool_a, res_a, tool_b, res_b)
                
                if comp_a == ComparisonStatus.MATCH:
                    metric_a = "aTN" if exec_a == ExecutionStatus.SUCCESS else "aTP"
                    metric_b = "aFN" if exec_b == ExecutionStatus.SUCCESS else "aFP"
                    result.stats_a.add(metric_a, scenario)
                    result.stats_b.add(metric_b, scenario)
                else:
                    metric_b = "aTN" if exec_b == ExecutionStatus.SUCCESS else "aTP"
                    metric_a = "aFN" if exec_a == ExecutionStatus.SUCCESS else "aFP"
                    result.stats_b.add(metric_b, scenario)
                    result.stats_a.add(metric_a, scenario)
        return result

    def _print_divergence(self, scenario, name_a, res_a, name_b, res_b):
        rprint(f"[bold red]Divergence detected between {name_a} and {name_b} for scenario {scenario}[/bold red]")
        rprint(f"Expected: {self.expected_map.get(scenario)}")
        rprint(f"{name_a} - Execution: {res_a.execution}, Comparison: {res_a.comparison}")
        rprint(f"{name_b} - Execution: {res_b.execution}, Comparison: {res_b.comparison}\n")

# --- Rendering ---

class ResultsRenderer:
    @staticmethod
    def print_confusion_matrix(tool_name: str, matrix: dict):
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Metric")
        table.add_column("Count")
        table.add_column("Scenarios")

        for key in ["TP", "TN", "FP", "FN", "error"]:
            bucket = matrix[key]
            table.add_row(key, str(bucket.count), bucket.scenario_str)

        rprint(Panel(table, title=f"[bold]Tool: {tool_name}[/bold]", border_style="magenta"))

    @staticmethod
    def print_pairwise(result: PairwiseResult):
        rprint(Panel(f"[bold]Comparison between {result.tool_a_name} and {result.tool_b_name}[/bold]", border_style="blue"))
        
        def render_stats(tool_name: str, stats: SingleToolPairwiseStats):
            table = Table(show_header=True, header_style="bold cyan", title=f"[bold underline]{tool_name} Metrics[/bold underline]")
            table.add_column("Metric")
            table.add_column("Count", justify="right")
            table.add_column("Scenarios")
            
            # Use specific order from original script
            metrics = [
                ("aTP", stats.atp),
                ("aTN", stats.atn),
                ("aFP", stats.afp),
                ("aFN", stats.afn)
            ]
            
            for label, bucket in metrics:
                table.add_row(label, str(bucket.count), bucket.scenario_str)
            
            rprint(table)

        render_stats(result.tool_a_name, result.stats_a)
        rprint("\n") # Spacer
        render_stats(result.tool_b_name, result.stats_b)
        rprint("\n")

# --- Main ---

def load_data(json_path: Path) -> Tuple[Dict[str, Dict[str, ToolScenarioResult]], Dict[str, str]]:
    with open(json_path, 'r') as f:
        raw_data = json.load(f)

    tool_results = { "diff3": {}, "mergiraf-semi": {}, "mergiraf": {} }
    expected_map = {}

    for scenario, data in raw_data.items():
        expected_map[scenario] = data.get("expected", "UNKNOWN")
        
        for tool in tool_results.keys():
            t_data = data.get(tool, {})
            # Safely handle enums that might match partial strings from original JSON
            exec_str = t_data.get("execution", "NO_OUTPUT")
            comp_str = t_data.get("comparison", "NO_OUTPUT")
            
            # Map raw strings to Enums (simple mapping)
            if "FAILED" in exec_str: e_stat = ExecutionStatus.FAILED
            elif "SUCCESS" in exec_str: e_stat = ExecutionStatus.SUCCESS
            elif "CONFLICT" in exec_str: e_stat = ExecutionStatus.CONFLICT
            else: e_stat = ExecutionStatus.NO_OUTPUT
            
            c_stat = ComparisonStatus.MATCH if comp_str == "MATCH" else ComparisonStatus.DIFFER
            if comp_str == "NO_OUTPUT": c_stat = ComparisonStatus.NO_OUTPUT

            tool_results[tool][scenario] = ToolScenarioResult(e_stat, c_stat)

    return tool_results, expected_map

def main():
    parser = argparse.ArgumentParser(description="Compute comparison metrics from scenarios.json")
    parser.add_argument("--debug", action="store_true", help="Enable detailed debug output")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    scenarios_json = repo_root / "examples" / "swift" / "scenarios.json"

    if not scenarios_json.exists():
        rprint(f"[red]scenarios.json not found at {scenarios_json}[/red]")
        sys.exit(1)

    tool_data, expected_map = load_data(scenarios_json)

    # 1. Confusion Matrices
    for tool_name, results in tool_data.items():
        matrix = StatisticsCalculator.compute_confusion_matrix(tool_name, results)
        ResultsRenderer.print_confusion_matrix(tool_name, matrix)

    # 2. Pairwise Comparisons
    comparator = PairwiseComparator(tool_data, expected_map, debug=args.debug)
    pairs = [
        ("diff3", "mergiraf"),
        ("diff3", "mergiraf-semi"),
        ("mergiraf-semi", "mergiraf")
    ]

    for t_a, t_b in pairs:
        result = comparator.compare(t_a, t_b)
        ResultsRenderer.print_pairwise(result)

if __name__ == "__main__":
    main()