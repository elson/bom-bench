# Contributing to bom-bench

Thank you for your interest in contributing to bom-bench! This document provides guidelines for extending the project with new package managers, data sources, and SCA tool integrations.

## Table of Contents

- [Development Setup](#development-setup)
- [Adding a New Package Manager](#adding-a-new-package-manager)
- [Adding a New Data Source](#adding-a-new-data-source)
- [Adding SCA Tool Integration](#adding-sca-tool-integration)
- [Testing Guidelines](#testing-guidelines)
- [Code Style](#code-style)

## Development Setup

### Prerequisites

- Python ≥ 3.12
- UV or pip package manager
- Git

### Installation

```bash
# Clone the repository
git clone https://github.com/your-org/bom-bench
cd bom-bench

# Install in editable mode
uv pip install -e ".[dev]"

# Run tests to verify setup
uv run pytest tests/ -v
```

### Project Structure

```
src/bom_bench/
├── cli.py                  # CLI orchestration
├── config.py               # Configuration constants
├── data/                   # Data source plugins
├── package_managers/       # Package manager plugins
├── generators/             # Manifest generators
├── models/                 # Data models
└── benchmarking/           # SCA tool integration
```

## Adding a New Package Manager

Package managers are plugins that generate manifests and lock files for specific package ecosystems.

### Step 1: Create Implementation File

Create `src/bom_bench/package_managers/{pm_name}.py`:

```python
"""Package manager implementation for {PM_NAME}."""

from pathlib import Path
from bom_bench.models.scenario import Scenario
from bom_bench.models.result import LockResult, LockStatus
from bom_bench.package_managers.base import PackageManager


class {PMName}PackageManager(PackageManager):
    """{PM_NAME} package manager implementation."""

    name = "{pm_name}"  # lowercase name
    ecosystem = "{ecosystem}"  # python, javascript, java, etc.

    def generate_manifest(
        self,
        scenario: Scenario,
        output_dir: Path
    ) -> Path:
        """Generate manifest file for {PM_NAME}.

        Args:
            scenario: Scenario to generate manifest for
            output_dir: Directory where manifest should be written

        Returns:
            Path to the generated manifest file
        """
        # 1. Extract dependencies from scenario.root.requires
        # 2. Use generator (if needed) to create manifest content
        # 3. Write to output_dir
        # 4. Return path to manifest file
        pass

    def run_lock(
        self,
        project_dir: Path,
        scenario_name: str,
        timeout: int = 120
    ) -> LockResult:
        """Execute lock command for {PM_NAME}.

        Args:
            project_dir: Directory containing manifest file
            scenario_name: Name of the scenario
            timeout: Command timeout in seconds

        Returns:
            LockResult with execution details
        """
        # 1. Run lock command (e.g., pip-compile, pnpm install --lockfile-only)
        # 2. Capture stdout/stderr to output file
        # 3. Check if lock file was generated
        # 4. Return LockResult with status and paths
        pass

    def validate_scenario(self, scenario: Scenario) -> bool:
        """Check if scenario is compatible.

        Args:
            scenario: Scenario to validate

        Returns:
            True if scenario is compatible
        """
        # Check scenario.source against supported data sources
        return scenario.source in ["your-supported-source"]
```

### Step 2: Create Generator (If Needed)

For complex manifest formats, create a generator:

`src/bom_bench/generators/{pm_name}/{manifest_name}.py`

Example for pip's requirements.in:

```python
"""requirements.in generation for pip."""

from typing import List

def generate_requirements_in(dependencies: List[str]) -> str:
    """Generate requirements.in content.

    Args:
        dependencies: List of requirement strings

    Returns:
        requirements.in file content
    """
    return "\n".join(dependencies) + "\n"
```

### Step 3: Register Package Manager

Update `src/bom_bench/package_managers/__init__.py`:

```python
from bom_bench.package_managers.{pm_name} import {PMName}PackageManager

PACKAGE_MANAGERS: Dict[str, Type[PackageManager]] = {
    "uv": UVPackageManager,
    "{pm_name}": {PMName}PackageManager,  # Add your PM
}
```

### Step 4: Update Configuration

Add to `src/bom_bench/config.py`:

```python
DATA_SOURCE_PM_MAPPING = {
    "packse": ["uv", "pip", "{pm_name}"],  # If applicable
    "{your-source}": ["{pm_name}"],
}
```

### Step 5: Add Tests

Create tests in `tests/unit/test_package_managers.py`:

```python
class Test{PMName}PackageManager:
    """Test {PM_NAME} package manager."""

    @pytest.fixture
    def pm(self):
        return {PMName}PackageManager()

    def test_name_and_ecosystem(self, pm):
        assert pm.name == "{pm_name}"
        assert pm.ecosystem == "{ecosystem}"

    def test_generate_manifest(self, pm):
        # Test manifest generation
        pass

    def test_run_lock(self, pm):
        # Test lock file generation
        pass
```

## Adding a New Data Source

Data sources fetch and normalize test scenarios from external sources.

### Step 1: Create Implementation File

Create `src/bom_bench/data/sources/{source_name}.py`:

```python
"""Data source for {SOURCE_NAME}."""

from pathlib import Path
from typing import List
from bom_bench.data.base import DataSource
from bom_bench.models.scenario import Scenario, Root, Requirement, ResolverOptions


class {SourceName}DataSource(DataSource):
    """{SOURCE_NAME} data source implementation."""

    name = "{source_name}"
    supported_pms = ["{pm1}", "{pm2}"]  # PMs that can use this source

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir

    def fetch(self) -> None:
        """Fetch data from source."""
        # Download or clone source data to self.data_dir
        # Examples:
        # - git clone https://github.com/org/repo self.data_dir
        # - Download tarball and extract
        # - Use API to fetch test cases
        pass

    def load_scenarios(self) -> List[Scenario]:
        """Load and normalize scenarios.

        Returns:
            List of normalized Scenario objects
        """
        scenarios = []

        # 1. Find source files (package.json, build.gradle, etc.)
        # 2. Parse each file
        # 3. Extract dependencies
        # 4. Normalize to Scenario format:
        #    - name: Unique scenario identifier
        #    - root.requires: List of Requirement objects
        #    - resolver_options: PM-specific options
        #    - source: "{source_name}"

        for source_file in self._find_source_files():
            scenario = self._parse_file(source_file)
            scenarios.append(scenario)

        return scenarios

    def needs_fetch(self) -> bool:
        """Check if fetch is needed."""
        return not self.data_dir.exists() or not any(self.data_dir.iterdir())

    def _find_source_files(self) -> List[Path]:
        """Find all source files in data directory."""
        # Implementation specific to your source
        pass

    def _parse_file(self, file_path: Path) -> Scenario:
        """Parse a single source file into a Scenario."""
        # Parse and normalize
        pass
```

### Step 2: Register Data Source

Update `src/bom_bench/data/__init__.py`:

```python
from bom_bench.data.sources.{source_name} import {SourceName}DataSource

DATA_SOURCES: Dict[str, Type[DataSource]] = {
    "packse": PackseDataSource,
    "{source_name}": {SourceName}DataSource,  # Add your source
}
```

### Step 3: Update Configuration

Add to `src/bom_bench/config.py`:

```python
DATA_SOURCE_PM_MAPPING = {
    "packse": ["uv", "pip"],
    "{source_name}": ["{pm1}", "{pm2}"],  # Add mapping
}

DEFAULT_{SOURCE_NAME}_DIR = DATA_DIR / "{source_name}"
```

### Step 4: Add Tests

Create tests in `tests/unit/test_data_sources.py`:

```python
class Test{SourceName}DataSource:
    """Test {SOURCE_NAME} data source."""

    def test_init(self):
        # Test initialization
        pass

    def test_fetch(self):
        # Test data fetching
        pass

    def test_load_scenarios(self):
        # Test scenario loading and normalization
        pass
```

## Adding SCA Tool Integration

SCA tool integrations scan generated outputs for vulnerabilities.

### Step 1: Implement Tool Runner

Create implementation in `src/bom_bench/benchmarking/runner.py`:

```python
class {ToolName}Runner(SCAToolRunner):
    """{TOOL_NAME} SCA tool runner."""

    tool_name = "{tool_name}"

    def check_available(self) -> bool:
        """Check if {TOOL_NAME} is installed."""
        try:
            result = subprocess.run(
                ["{tool_command}", "--version"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def run(
        self,
        project_dir: Path,
        package_manager: str,
        scenario_name: str
    ) -> Dict[str, Any]:
        """Run {TOOL_NAME} scan."""
        # 1. Execute tool command
        # 2. Parse JSON output
        # 3. Return normalized results
        pass
```

### Step 2: Add Result Parser

Update `src/bom_bench/benchmarking/collectors.py`:

```python
def add_{tool_name}_result(
    self,
    scenario_name: str,
    package_manager: str,
    tool_output: Dict[str, Any],
    duration: float
) -> None:
    """Parse and add {TOOL_NAME} results."""
    findings = []

    # Parse tool_output and create VulnerabilityFinding objects
    for vuln in tool_output.get("vulnerabilities", []):
        finding = VulnerabilityFinding(
            package_name=vuln["package"],
            package_version=vuln["version"],
            vulnerability_id=vuln["id"],
            severity=self._map_severity(vuln["severity"]),
            description=vuln.get("description"),
            fixed_version=vuln.get("fixed_version"),
            tool_name="{tool_name}"
        )
        findings.append(finding)

    scan_result = ScanResult(
        scenario_name=scenario_name,
        package_manager=package_manager,
        tool_name="{tool_name}",
        findings=findings,
        scan_duration_seconds=duration
    )

    self.results.append(scan_result)
```

## Testing Guidelines

### Running Tests

```bash
# Run all tests
uv run pytest tests/ -v

# Run specific test file
uv run pytest tests/unit/test_package_managers.py -v

# Run with coverage
uv run pytest tests/ --cov=bom_bench --cov-report=html

# Run specific test
uv run pytest tests/unit/test_package_managers.py::TestUVPackageManager::test_name_and_ecosystem -v
```

### Writing Tests

- **Unit tests**: Test individual components in isolation
- **Integration tests**: Test component interactions
- **Use fixtures**: Create reusable test data
- **Use mocks**: Mock external dependencies (subprocess, API calls)
- **Test edge cases**: Empty inputs, errors, timeouts

Example test structure:

```python
class TestYourComponent:
    """Test suite for YourComponent."""

    @pytest.fixture
    def component(self):
        """Create component instance."""
        return YourComponent()

    def test_basic_functionality(self, component):
        """Test basic functionality."""
        result = component.do_something()
        assert result == expected_value

    def test_error_handling(self, component):
        """Test error handling."""
        with pytest.raises(ExpectedError):
            component.do_invalid_thing()
```

## Code Style

### Python Style Guide

- Follow PEP 8
- Use type hints for all function signatures
- Use dataclasses for data models
- Use ABC for interfaces
- Maximum line length: 100 characters

### Code Quality Tools

```bash
# Format code
ruff format src/bom_bench/

# Lint code
ruff check src/bom_bench/

# Type checking
mypy src/bom_bench/
```

### Docstring Format

Use Google-style docstrings:

```python
def function_name(arg1: str, arg2: int) -> bool:
    """Short description of function.

    Longer description if needed.

    Args:
        arg1: Description of arg1
        arg2: Description of arg2

    Returns:
        Description of return value

    Raises:
        ValueError: When something goes wrong
    """
    pass
```

## Pull Request Guidelines

1. **Create a feature branch**: `git checkout -b feature/your-feature`
2. **Write tests**: Ensure test coverage for new code
3. **Update documentation**: Update README.md, docstrings
4. **Run tests**: Ensure all tests pass
5. **Format code**: Run ruff format
6. **Commit**: Use descriptive commit messages
7. **Push**: `git push origin feature/your-feature`
8. **Create PR**: Provide clear description of changes

### Commit Message Format

```
type: short description

Longer description if needed.

- Bullet points for details
- More details

Fixes #123
```

Types: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`

## Questions?

If you have questions or need help, please:
- Open an issue on GitHub
- Check existing issues for similar questions
- Review the code documentation

Thank you for contributing to bom-bench!
