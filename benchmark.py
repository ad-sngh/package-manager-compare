#!/usr/bin/env python3
"""
Benchmark script to compare Python package managers.
Measures installation time, lock file size, and memory usage.
"""

import os
import sys
import json
import time
import shutil
import subprocess
import argparse
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Optional, List


@dataclass
class BenchmarkResult:
    tool: str
    run_number: int
    install_time: float
    lock_file_size: int
    lock_file_path: str
    packages_count: int
    success: bool
    error_message: Optional[str] = None
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class PackageManagerBenchmark:
    def __init__(self, packages_file: str = "packages.txt", runs: int = 3, verbose: bool = False):
        self.packages_file = packages_file
        self.runs = runs
        self.verbose = verbose
        self.results_dir = Path("results")
        self.results_dir.mkdir(exist_ok=True)
        
        # Load packages
        with open(packages_file) as f:
            self.packages = [line.strip() for line in f if line.strip()]
        
        print(f"📦 Loaded {len(self.packages)} packages from {packages_file}")
        print(f"🔄 Running {runs} iterations per tool")
        print()
    
    def log(self, message: str, verbose_only: bool = False):
        if verbose_only and not self.verbose:
            return
        print(message)
    
    def _get_file_size(self, path: Path) -> int:
        """Get file size in bytes."""
        if path.exists():
            return path.stat().st_size
        return 0
    
    def _run_command(self, cmd: List[str], cwd: Path) -> tuple[bool, str, float]:
        """Run a command and measure execution time."""
        try:
            start = time.time()
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            elapsed = time.time() - start
            
            if result.returncode != 0:
                error = result.stderr or result.stdout
                return False, error, elapsed
            
            return True, result.stdout, elapsed
        except subprocess.TimeoutExpired:
            return False, "Command timed out after 5 minutes", 300
        except Exception as e:
            return False, str(e), 0
    
    def benchmark_pip(self) -> List[BenchmarkResult]:
        """Benchmark pip + venv."""
        print("🔧 Benchmarking pip + venv...")
        results = []
        
        for run in range(1, self.runs + 1):
            test_dir = Path(f"test_pip_run{run}")
            if test_dir.exists():
                shutil.rmtree(test_dir)
            test_dir.mkdir()
            
            try:
                # Create venv
                self.log(f"  Run {run}: Creating venv...", verbose_only=True)
                success, output, _ = self._run_command(
                    ["python3", "-m", "venv", "venv"],
                    test_dir
                )
                if not success:
                    results.append(BenchmarkResult(
                        tool="pip",
                        run_number=run,
                        install_time=0,
                        lock_file_size=0,
                        lock_file_path="",
                        packages_count=len(self.packages),
                        success=False,
                        error_message=f"Failed to create venv: {output}"
                    ))
                    continue
                
                # Install packages
                self.log(f"  Run {run}: Installing packages...", verbose_only=True)
                pip_cmd = [
                    str(test_dir / "venv" / "bin" / "pip"),
                    "install",
                    "-q"
                ] + self.packages
                
                success, output, install_time = self._run_command(pip_cmd, test_dir)
                
                # Generate requirements.txt
                req_file = test_dir / "requirements.txt"
                freeze_cmd = [
                    str(test_dir / "venv" / "bin" / "pip"),
                    "freeze"
                ]
                success_freeze, freeze_output, _ = self._run_command(freeze_cmd, test_dir)
                
                if success_freeze:
                    req_file.write_text(freeze_output)
                
                lock_size = self._get_file_size(req_file)
                
                result = BenchmarkResult(
                    tool="pip",
                    run_number=run,
                    install_time=install_time,
                    lock_file_size=lock_size,
                    lock_file_path=str(req_file),
                    packages_count=len(self.packages),
                    success=success,
                    error_message=None if success else output
                )
                results.append(result)
                self.log(f"  Run {run}: ✅ {install_time:.2f}s | Lock: {lock_size/1024:.1f}KB")
                
            finally:
                if test_dir.exists():
                    shutil.rmtree(test_dir)
        
        return results
    
    def benchmark_poetry(self) -> List[BenchmarkResult]:
        """Benchmark poetry + pyenv."""
        print("🔧 Benchmarking poetry + pyenv...")
        results = []
        
        for run in range(1, self.runs + 1):
            test_dir = Path(f"test_poetry_run{run}")
            if test_dir.exists():
                shutil.rmtree(test_dir)
            test_dir.mkdir()
            
            try:
                # Create pyproject.toml
                self.log(f"  Run {run}: Creating project...", verbose_only=True)
                pyproject = test_dir / "pyproject.toml"
                pyproject.write_text("""[tool.poetry]
name = "benchmark"
version = "0.1.0"
description = ""

[tool.poetry.dependencies]
python = "^3.10"
""")
                
                # Add packages
                self.log(f"  Run {run}: Installing packages...", verbose_only=True)
                for package in self.packages:
                    success, output, _ = self._run_command(
                        ["poetry", "add", "-q", package],
                        test_dir
                    )
                    if not success:
                        self.log(f"    Warning: Failed to add {package}: {output}", verbose_only=True)
                
                # Measure lock file generation
                lock_file = test_dir / "poetry.lock"
                start = time.time()
                success, output, _ = self._run_command(
                    ["poetry", "lock", "--no-update"],
                    test_dir
                )
                lock_time = time.time() - start
                
                lock_size = self._get_file_size(lock_file)
                
                result = BenchmarkResult(
                    tool="poetry",
                    run_number=run,
                    install_time=lock_time,
                    lock_file_size=lock_size,
                    lock_file_path=str(lock_file),
                    packages_count=len(self.packages),
                    success=success,
                    error_message=None if success else output
                )
                results.append(result)
                self.log(f"  Run {run}: ✅ {lock_time:.2f}s | Lock: {lock_size/1024:.1f}KB")
                
            finally:
                if test_dir.exists():
                    shutil.rmtree(test_dir)
        
        return results
    
    def benchmark_uv(self, use_requirements_file: bool = False) -> List[BenchmarkResult]:
        """Benchmark uv."""
        print("🔧 Benchmarking uv...")
        results = []
        
        for run in range(1, self.runs + 1):
            test_dir = Path(f"test_uv_run{run}")
            if test_dir.exists():
                shutil.rmtree(test_dir)
            test_dir.mkdir()
            
            try:
                if use_requirements_file:
                    # Use requirements.txt directly
                    self.log(f"  Run {run}: Creating requirements.txt...", verbose_only=True)
                    req_file = test_dir / "requirements.txt"
                    req_file.write_text("\n".join(self.packages))
                    
                    self.log(f"  Run {run}: Installing from requirements.txt...", verbose_only=True)
                    start = time.time()
                    success, output, _ = self._run_command(
                        ["uv", "pip", "compile", str(req_file), "-o", "uv.lock"],
                        test_dir
                    )
                    install_time = time.time() - start
                    
                    lock_file = test_dir / "uv.lock"
                else:
                    # Create pyproject.toml
                    self.log(f"  Run {run}: Creating project...", verbose_only=True)
                    pyproject = test_dir / "pyproject.toml"
                    pyproject.write_text("""[project]
name = "benchmark"
version = "0.1.0"
description = ""
requires-python = ">=3.10"
dependencies = []
""")
                    
                    # Install packages and measure time
                    self.log(f"  Run {run}: Installing packages...", verbose_only=True)
                    start = time.time()
                    success, output, _ = self._run_command(
                        ["uv", "add"] + self.packages,
                        test_dir
                    )
                    install_time = time.time() - start
                    
                    lock_file = test_dir / "uv.lock"
                
                lock_size = self._get_file_size(lock_file)
                
                result = BenchmarkResult(
                    tool="uv",
                    run_number=run,
                    install_time=install_time,
                    lock_file_size=lock_size,
                    lock_file_path=str(lock_file),
                    packages_count=len(self.packages),
                    success=success,
                    error_message=None if success else output
                )
                results.append(result)
                self.log(f"  Run {run}: ✅ {install_time:.2f}s | Lock: {lock_size/1024:.1f}KB")
                
            finally:
                if test_dir.exists():
                    shutil.rmtree(test_dir)
        
        return results
    
    def run_all(self, uv_use_requirements: bool = False) -> dict:
        """Run all benchmarks."""
        all_results = {
            "pip": self.benchmark_pip(),
            "poetry": self.benchmark_poetry(),
            "uv": self.benchmark_uv(use_requirements_file=uv_use_requirements)
        }
        return all_results
    
    def print_summary(self, all_results: dict):
        """Print summary of results."""
        print("\n" + "="*70)
        print("📊 BENCHMARK SUMMARY")
        print("="*70 + "\n")
        
        for tool, results in all_results.items():
            successful = [r for r in results if r.success]
            if not successful:
                print(f"❌ {tool.upper()}: All runs failed")
                continue
            
            times = [r.install_time for r in successful]
            sizes = [r.lock_file_size for r in successful]
            
            avg_time = sum(times) / len(times)
            avg_size = sum(sizes) / len(sizes)
            min_time = min(times)
            max_time = max(times)
            
            print(f"✅ {tool.upper()}")
            print(f"   Installation Time: {avg_time:.2f}s (min: {min_time:.2f}s, max: {max_time:.2f}s)")
            print(f"   Lock File Size: {avg_size/1024:.1f}KB")
            print(f"   Successful Runs: {len(successful)}/{len(results)}")
            print()
        
        # Save detailed results
        results_file = self.results_dir / f"benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        results_data = {
            tool: [asdict(r) for r in results]
            for tool, results in all_results.items()
        }
        with open(results_file, "w") as f:
            json.dump(results_data, f, indent=2)
        print(f"📁 Detailed results saved to: {results_file}")


def main():
    parser = argparse.ArgumentParser(description="Benchmark Python package managers")
    parser.add_argument("--tool", choices=["pip", "poetry", "uv"], help="Run specific tool only")
    parser.add_argument("--runs", type=int, default=3, help="Number of runs per tool")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--packages", default="packages.txt", help="Path to packages file")
    parser.add_argument("--uv-requirements", action="store_true", help="Use requirements.txt with uv pip compile")
    
    args = parser.parse_args()
    
    benchmark = PackageManagerBenchmark(
        packages_file=args.packages,
        runs=args.runs,
        verbose=args.verbose
    )
    
    if args.tool:
        if args.tool == "pip":
            results = {"pip": benchmark.benchmark_pip()}
        elif args.tool == "poetry":
            results = {"poetry": benchmark.benchmark_poetry()}
        else:
            results = {"uv": benchmark.benchmark_uv(use_requirements_file=args.uv_requirements)}
    else:
        results = benchmark.run_all(uv_use_requirements=args.uv_requirements)
    
    benchmark.print_summary(results)


if __name__ == "__main__":
    main()
