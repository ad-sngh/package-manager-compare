# Python Package Manager Comparison

Practical benchmarks comparing `pip + venv`, `poetry + pyenv`, and `uv` for dependency management.

This repo contains scripts to measure:
- Time taken to resolve and install 50 common packages
- Lock file sizes
- Memory usage during installation
- Reproducibility across runs

## Setup

### Prerequisites

- Python 3.10+
- `pip`, `poetry`, `pyenv`, and `uv` installed
- `time` command available (macOS/Linux)
- ~2GB free disk space for test environments

### Installation

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install poetry
curl -sSL https://install.python-poetry.org | python3 -

# Install pyenv
brew install pyenv  # macOS
# or: git clone https://github.com/pyenv/pyenv.git ~/.pyenv  # Linux

# Install Python 3.12 (if not already installed)
pyenv install 3.12.0
```

## Running the Benchmarks

```bash
# Run all benchmarks
python benchmark.py

# Run specific benchmark
python benchmark.py --tool pip
python benchmark.py --tool poetry
python benchmark.py --tool uv

# Verbose output with detailed timing
python benchmark.py --verbose
```

## Results

See `results/` directory for detailed benchmark results and analysis.

## Packages Tested

The benchmark installs 50 commonly used packages:
- Web frameworks: `fastapi`, `flask`, `django`
- Data science: `pandas`, `numpy`, `scikit-learn`, `matplotlib`
- ML: `torch`, `tensorflow`
- Utilities: `requests`, `click`, `pydantic`, etc.

See `packages.txt` for the full list.
