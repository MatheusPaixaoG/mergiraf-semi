#!/usr/bin/env python3
"""
Compute Comparison Metrics for Merge Tools

This script analyzes the results from scenarios.json and generates comprehensive
comparison metrics between different merge tools (diff3, mergiraf, mergiraf-semi).

It provides:
1. Confusion matrices for each tool showing TP, TN, FP, FN, and errors
2. Pairwise comparisons between tools showing additional metrics (aTP, aTN, aFP, aFN)
3. Detailed scenario lists for each metric

Usage:
    python compute_comparison_metrics.py [--debug]

Options:
    --debug    Enable detailed debug output showing scenario-by-scenario analysis

The script reads from examples/swift/scenarios.json which contains expected results
and actual tool outputs for each test scenario.
"""

import json
import subprocess
import sys
import argparse
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

class ToolExecutionResult:
    def __init__(self, tool_name: str):        
        self.tool_name = tool_name
        self.outputs = {}

    def confusion_matrix(self):
        scenarios = {
            "TP": [],
            "TN": [],
            "FP": [],
            "FN": [],
            "error": []
        }
        results = {
            "TP": 0,
            "TN": 0,
            "FP": 0,
            "FN": 0,
            "error": 0
        }

        # SUCCESS means that a merge has occurred
        # FAILED means that an error has occured
        # CONFLICTS means that a conflict has been detected
        
        for (scenario, status) in self.outputs.items():            
            execution, comparison = status            

            made_merge = (execution == "SUCCESS")

            if "FAILED" in execution or "NO_OUTPUT" in execution:
                matrix = "error"                
            elif made_merge:
                matrix = "TN" if comparison == "MATCH" else "FN"                        
            else:
                matrix = "TP" if comparison == "MATCH" else "FP"

            scenarios[matrix].append(scenario)
            results[matrix] += 1
        
        return {
            "tool": self.tool_name,            
            "scenarios": scenarios,
            "results": results
        }
    
    def add_output(self, scenario: str, status: tuple):
        self.outputs[scenario] = status

def print_confusion_matrix(json_tool_results: dict):    
    # Use the confusion_matrix method from ToolExecutionResult
    for (tool_name, result) in json_tool_results.items():
        matrix = result.confusion_matrix()
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Metric")
        table.add_column("Count")
        table.add_column("Scenarios")

        for key in ["TP", "TN", "FP", "FN", "error"]:
            count = matrix["results"][key]
            scenario_list = ", ".join(matrix["scenarios"][key]) if matrix["scenarios"][key] else "-"
            table.add_row(key, str(count), scenario_list)

        rprint(Panel(table, title=f"[bold]Tool: {tool_name}[/bold]", border_style="magenta"))

def compute_comparison_metrics(json_tool_results, expected_by_scenario: dict, debug: bool = False):
    pairs_of_tools = [
        ("diff3", "mergiraf"),
        ("diff3", "mergiraf-semi"),
        ("mergiraf-semi", "mergiraf")
    ]

    comparison_results = {}
    for tool_a, tool_b in pairs_of_tools:
        comparison = {
            tool_a: {"aTP": 0, "aTN": 0, "aFP": 0, "aFN": 0, "scenarios": {"aTP": [], "aTN": [], "aFP": [], "aFN": []}},
            tool_b: {"aTP": 0, "aTN": 0, "aFP": 0, "aFN": 0, "scenarios": {"aTP": [], "aTN": [], "aFP": [], "aFN": []}}
        }
        for scenario in expected_by_scenario.keys():
            execution_status_a, comparison_status_a = json_tool_results[tool_a].outputs.get(scenario, ("UNKNOWN_EXECUTION", "NO_OUTPUT"))
            execution_status_b, comparison_status_b = json_tool_results[tool_b].outputs.get(scenario, ("UNKNOWN_EXECUTION", "NO_OUTPUT"))
            
            # A fails, but B succeeds. We only care about this scenario if B produces a correct output,
            # otherwise B would be "punished" twice, since A cannot even get a returned value.
            if execution_status_a == "FAILED" and execution_status_b != "FAILED":
                if comparison_status_b == "MATCH":
                    if debug:
                        rprint(f"[green]{tool_b} succeeded where {tool_a} failed and produced the expected output for scenario {scenario}.[/green]\n")
                    metric = "aTN" if execution_status_b == "SUCCESS" else "aTP"
                    comparison[tool_b][metric] += 1
                    comparison[tool_b]["scenarios"][metric].append(scenario)
                else:
                    if debug:
                        rprint(f"[yellow]{tool_b} succeeded where {tool_a} failed, but did not produce the expected output for scenario {scenario}.[/yellow]\n")
                continue

            # B fails, but A succeeds. We only care about this scenario if A produces a correct output,
            # otherwise A would be "punished" twice, since B cannot even get a returned value.
            if execution_status_b == "FAILED" and execution_status_a != "FAILED":
                if comparison_status_a == "MATCH":
                    if debug:
                        rprint(f"[green]{tool_a} succeeded where {tool_b} failed and produced the expected output for scenario {scenario}.[/green]\n")
                    metric = "aTN" if execution_status_a == "SUCCESS" else "aTP"
                    comparison[tool_a][metric] += 1
                    comparison[tool_a]["scenarios"][metric].append(scenario)
                else:
                    if debug:
                        rprint(f"[yellow]{tool_a} succeeded where {tool_b} failed, but did not produce the expected output for scenario {scenario}.[/yellow]\n")
                continue
            
            # Both tools produced the same action (Merge == SUCCESS // Report == CONFLICT))
            if execution_status_a == execution_status_b:
                # If the comparison with the expected output is also the same, we skip this scenario
                # since we dont need to compare the differences between them for this scenario.
                if comparison_status_a == comparison_status_b:
                    if debug:
                        rprint(f"[yellow]Both tools produced the same result for scenario {scenario}.[/yellow]\n")
                    continue

                # Otherwise, we have a divergence in the outputs of both tools.
                if debug:
                    rprint(f"[bold red]Divergence detected between {tool_a} and {tool_b} for scenario {scenario}[/bold red]")
                    rprint(f"Expected output: {expected_by_scenario[scenario]}")
                    rprint(f"{tool_a} - Execution: {execution_status_a}, Comparison: {comparison_status_a}")
                    rprint(f"{tool_b} - Execution: {execution_status_b}, Comparison: {comparison_status_b}\n")
                # Now we evaluate which tool was correct based on the expected output
                if comparison_status_a == "MATCH":
                    if debug:
                        rprint(f"[green]{tool_a} produced the expected output for scenario {scenario}.[/green]\n")
                    metric_a = "aTN" if execution_status_a == "SUCCESS" else "aTP"
                    metric_b = "aFN" if execution_status_b == "SUCCESS" else "aFP"
                    comparison[tool_a][metric_a] += 1
                    comparison[tool_a]["scenarios"][metric_a].append(scenario)
                    comparison[tool_b][metric_b] += 1
                    comparison[tool_b]["scenarios"][metric_b].append(scenario)
                else:
                    if debug:
                        rprint(f"[green]{tool_b} produced the expected output for scenario {scenario}.[/green]\n")
                    metric_b = "aTN" if execution_status_b == "SUCCESS" else "aTP"
                    metric_a = "aFN" if execution_status_a == "SUCCESS" else "aFP"
                    comparison[tool_b][metric_b] += 1
                    comparison[tool_b]["scenarios"][metric_b].append(scenario)
                    comparison[tool_a][metric_a] += 1
                    comparison[tool_a]["scenarios"][metric_a].append(scenario)
            # They reported a different execution status (one merged, the other reported conflicts)
            else:
                if debug:
                    rprint(f"[bold red]Divergence detected between {tool_a} and {tool_b} for scenario {scenario}[/bold red]")
                    rprint(f"Expected output: {expected_by_scenario[scenario]}")
                    rprint(f"{tool_a} - Execution: {execution_status_a}, Comparison: {comparison_status_a}")
                    rprint(f"{tool_b} - Execution: {execution_status_b}, Comparison: {comparison_status_b}\n")
                
                if comparison_status_a == "MATCH":
                    if debug:
                        rprint(f"[green]{tool_a} produced the expected output for scenario {scenario}.[/green]\n")
                    metric_a = "aTN" if execution_status_a == "SUCCESS" else "aTP"
                    metric_b = "aFN" if execution_status_b == "SUCCESS" else "aFP"
                    comparison[tool_a][metric_a] += 1
                    comparison[tool_a]["scenarios"][metric_a].append(scenario)
                    comparison[tool_b][metric_b] += 1
                    comparison[tool_b]["scenarios"][metric_b].append(scenario)
                else:
                    if debug:
                        rprint(f"[green]{tool_b} produced the expected output for scenario {scenario}.[/green]\n")
                    metric_b = "aTN" if execution_status_b == "SUCCESS" else "aTP"
                    metric_a = "aFN" if execution_status_a == "SUCCESS" else "aFP"
                    comparison[tool_b][metric_b] += 1
                    comparison[tool_b]["scenarios"][metric_b].append(scenario)
                    comparison[tool_a][metric_a] += 1
                    comparison[tool_a]["scenarios"][metric_a].append(scenario)
        comparison_results[(tool_a, tool_b)] = comparison

    for (tool_a, tool_b), comparison in comparison_results.items():
        rprint(Panel(f"[bold]Comparison between {tool_a} and {tool_b}[/bold]", border_style="blue"))
        for tool, metrics in comparison.items():
            table = Table(show_header=True, header_style="bold cyan", title=f"[bold underline]{tool} Metrics[/bold underline]")
            table.add_column("Metric")
            table.add_column("Count", justify="right")
            table.add_column("Scenarios")
            
            for metric in ["aTP", "aTN", "aFP", "aFN"]:
                count = metrics[metric]
                scenario_list = ", ".join(metrics["scenarios"][metric]) if metrics["scenarios"][metric] else "-"
                table.add_row(metric, str(count), scenario_list)
            
            rprint(table)
            rprint("\n")


def main():
    parser = argparse.ArgumentParser(description="Compute comparison metrics from scenarios.json")
    parser.add_argument("--debug", action="store_true", help="Enable debug output for detailed scenario analysis", default=False)
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    examples_dir = repo_root / "examples" / "swift"

    if not examples_dir.is_dir():
        rprint(f"[red]Examples directory not found: {examples_dir}[/red]")
        sys.exit(1)

    # Read scenarios.json file and populate ToolExecutionResult with expected results
    scenarios_json_path = examples_dir / "scenarios.json"

    if scenarios_json_path.exists():
        with open(scenarios_json_path, 'r') as f:
            scenarios_data = json.load(f)
        
        # Create new ToolExecutionResult instances from scenarios.json
        json_tool_results = {
            "diff3": ToolExecutionResult("diff3"),
            "mergiraf-semi": ToolExecutionResult("mergiraf-semi"),
            "mergiraf": ToolExecutionResult("mergiraf")
        }
        expected_by_scenario = {}

        for scenario_name, scenario_data in scenarios_data.items():
            expected_by_scenario[scenario_name] = scenario_data.get("expected", "NO_OUTPUT")

            for tool_name in ["diff3", "mergiraf-semi", "mergiraf"]:
                tool_data = scenario_data.get(tool_name, {})
                execution = tool_data.get("execution", "NO_OUTPUT")
                comparison = tool_data.get("comparison", "NO_OUTPUT")
                json_tool_results[tool_name].add_output(scenario_name, (execution, comparison))

        print_confusion_matrix(json_tool_results)
        compute_comparison_metrics(json_tool_results, expected_by_scenario, debug=args.debug)

    else:
        rprint(f"[yellow]scenarios.json not found at {scenarios_json_path}[/yellow]")
        sys.exit(1)


if __name__ == "__main__":
    main()