#!/usr/bin/env python3
"""
Analyze benchmark results and generate visualizations.
"""

import json
import sys
from pathlib import Path
from statistics import mean, stdev
from typing import Dict, List


def load_results(results_file: str) -> Dict:
    """Load results from JSON file."""
    with open(results_file) as f:
        return json.load(f)


def analyze_results(results: Dict) -> Dict:
    """Analyze benchmark results."""
    analysis = {}
    
    for tool, runs in results.items():
        successful = [r for r in runs if r["success"]]
        
        if not successful:
            analysis[tool] = {
                "status": "FAILED",
                "successful_runs": 0,
                "total_runs": len(runs)
            }
            continue
        
        times = [r["install_time"] for r in successful]
        sizes = [r["lock_file_size"] for r in successful]
        
        analysis[tool] = {
            "status": "SUCCESS",
            "successful_runs": len(successful),
            "total_runs": len(runs),
            "install_time": {
                "mean": mean(times),
                "min": min(times),
                "max": max(times),
                "stdev": stdev(times) if len(times) > 1 else 0
            },
            "lock_file_size": {
                "mean": mean(sizes),
                "min": min(sizes),
                "max": max(sizes),
                "unit": "bytes"
            }
        }
    
    return analysis


def print_analysis(analysis: Dict):
    """Print analysis in a readable format."""
    print("\n" + "="*80)
    print("📊 DETAILED BENCHMARK ANALYSIS")
    print("="*80 + "\n")
    
    # Find fastest tool
    successful_tools = {
        tool: data for tool, data in analysis.items()
        if data["status"] == "SUCCESS"
    }
    
    if successful_tools:
        fastest_tool = min(
            successful_tools.items(),
            key=lambda x: x[1]["install_time"]["mean"]
        )
        print(f"⚡ Fastest Tool: {fastest_tool[0].upper()} ({fastest_tool[1]['install_time']['mean']:.2f}s)\n")
    
    for tool, data in analysis.items():
        print(f"{'='*40}")
        print(f"🔧 {tool.upper()}")
        print(f"{'='*40}")
        
        if data["status"] == "FAILED":
            print(f"❌ Status: FAILED")
            print(f"   Successful runs: {data['successful_runs']}/{data['total_runs']}")
            print()
            continue
        
        print(f"✅ Status: SUCCESS")
        print(f"   Successful runs: {data['successful_runs']}/{data['total_runs']}")
        print()
        
        # Installation time
        time_data = data["install_time"]
        print(f"⏱️  Installation Time:")
        print(f"   Mean:   {time_data['mean']:.2f}s")
        print(f"   Min:    {time_data['min']:.2f}s")
        print(f"   Max:    {time_data['max']:.2f}s")
        if time_data['stdev'] > 0:
            print(f"   StdDev: {time_data['stdev']:.2f}s")
        print()
        
        # Lock file size
        size_data = data["lock_file_size"]
        size_kb = size_data["mean"] / 1024
        print(f"📦 Lock File Size:")
        print(f"   Mean: {size_kb:.1f}KB ({size_data['mean']:.0f} bytes)")
        print(f"   Min:  {size_data['min']/1024:.1f}KB")
        print(f"   Max:  {size_data['max']/1024:.1f}KB")
        print()
    
    # Comparison table
    print("\n" + "="*80)
    print("📈 COMPARISON TABLE")
    print("="*80 + "\n")
    
    print(f"{'Tool':<12} {'Time (s)':<15} {'Lock Size (KB)':<15} {'Status':<10}")
    print("-" * 52)
    
    for tool, data in sorted(analysis.items()):
        if data["status"] == "SUCCESS":
            time_str = f"{data['install_time']['mean']:.2f}s"
            size_str = f"{data['lock_file_size']['mean']/1024:.1f}KB"
            status = "✅"
        else:
            time_str = "N/A"
            size_str = "N/A"
            status = "❌"
        
        print(f"{tool:<12} {time_str:<15} {size_str:<15} {status:<10}")
    
    print()


def generate_speedup_comparison(analysis: Dict):
    """Generate speedup comparison relative to pip."""
    print("\n" + "="*80)
    print("🚀 SPEEDUP COMPARISON (relative to pip)")
    print("="*80 + "\n")
    
    if "pip" not in analysis or analysis["pip"]["status"] != "SUCCESS":
        print("⚠️  pip benchmark not available for comparison\n")
        return
    
    pip_time = analysis["pip"]["install_time"]["mean"]
    
    for tool in ["poetry", "uv"]:
        if tool not in analysis or analysis[tool]["status"] != "SUCCESS":
            continue
        
        tool_time = analysis[tool]["install_time"]["mean"]
        speedup = pip_time / tool_time
        
        if speedup > 1:
            print(f"✨ {tool.upper()}: {speedup:.1f}x faster than pip")
        else:
            print(f"⚠️  {tool.upper()}: {1/speedup:.1f}x slower than pip")
    
    print()


def main():
    if len(sys.argv) < 2:
        print("Usage: python analyze_results.py <results_file.json>")
        print("\nExample: python analyze_results.py results/benchmark_20231115_143022.json")
        sys.exit(1)
    
    results_file = sys.argv[1]
    
    if not Path(results_file).exists():
        print(f"❌ Results file not found: {results_file}")
        sys.exit(1)
    
    results = load_results(results_file)
    analysis = analyze_results(results)
    
    print_analysis(analysis)
    generate_speedup_comparison(analysis)


if __name__ == "__main__":
    main()
