# Testing Guide for Fit File Faker

This document provides an overview of the test suite for Fit File Faker.

## Quick Start

```bash
# Run all tests
python3 run_tests.py

# Run with coverage (html report)
python3 run_tests.py --html
```

## Test Suite Overview

The test suite includes **53 tests** with **100% code coverage** for all major functionality:

### Test Coverage by Module

#### `test_fit_editor.py` (15 tests)
Tests for FIT file editing functionality:
- ✅ Editing files from all supported platforms (TPV, Zwift, MyWhoosh, Karoo, COROS)
- ✅ Manufacturer and device ID modification
- ✅ Device info message rewriting
- ✅ Activity data preservation
- ✅ Dryrun mode
- ✅ Invalid file handling
- ✅ Unknown field stripping

#### `test_config.py` (21 tests, 100% coverage)
Tests for configuration management:
- ✅ Config initialization and validation
- ✅ File I/O operations
- ✅ Interactive config building with questionary mocking
- ✅ Password masking in prompts
- ✅ Invalid input handling and warnings
- ✅ Keyboard interrupt handling
- ✅ Platform-specific path detection (macOS, Windows, Linux)
- ✅ TPV folder detection and user selection

#### `test_app.py` (32 tests, 100% coverage)
Tests for main application functionality:
- ✅ Garmin Connect upload (mocked)
- ✅ Authentication and credential handling
- ✅ HTTP error handling (409 conflicts, server errors)
- ✅ Interactive credential prompting
- ✅ Batch file processing (upload_all)
- ✅ File monitoring with watchdog
- ✅ CLI argument parsing and validation
- ✅ Verbose/non-verbose logging levels
- ✅ Python version checking
- ✅ Dryrun mode throughout

## Supported Platforms

The test suite verifies compatibility with FIT files from:
- **TrainingPeaks Virtual** (both older `tpv_20250111.fit` file and newer `tpv_20251120.fit`)
- **Zwift** (`zwift_20250401.fit`)
- **MyWhoosh** (`mywhoosh_20260111.fit`)
- **Hammerhead Karoo** (`karoo_20251119.fit`)
- **COROS** (`coros_20251118.fit`)

## Test Isolation

All tests are **completely isolated** from your real environment:

- ✅ Config directories redirected to temporary locations
- ✅ Cache directories use temp space
- ✅ No network calls (all external services mocked)
- ✅ Automatic cleanup after each test
- ✅ Safe to run in parallel

The `isolate_config_dirs` autouse fixture in `conftest.py` ensures that no test ever touches:
- Your real Garmin credentials
- Your actual FIT files
- Your user configuration directory
- Your system cache

## Test Fixtures and Helpers

The test suite uses shared fixtures in `conftest.py` to reduce duplication:

### Shared Mock Classes
- **`MockQuestion`**: Mock for questionary interactive prompts
- **`MockGarthHTTPError`**: Configurable HTTP error mock with status codes
- **`MockGarthException`**: Standard Garth exception for auth flow testing

### Shared Fixtures
- **`mock_garth_basic`**: Basic Garmin Connect mock for successful operations
- **`mock_garth_with_login`**: Garmin mock requiring authentication
- **`isolate_config_dirs`** (autouse): Automatically isolates all tests from real user directories
- **`temp_dir`**: Creates temporary directories for test outputs
- **`mock_config_file`**: Creates mock configuration files

These fixtures eliminate code duplication and make tests more maintainable.

## Mocking Strategy

### External Services
- **Garmin Connect** (`garth`): Mocked using `sys.modules` patching with shared fixtures
- **User prompts** (`questionary`): Mocked using `MockQuestion` helper class
- **File system** (`platformdirs`): Automatically redirected to temp directories via `isolate_config_dirs`

### Why sys.modules for garth?
The `garth` library is imported inside functions (lazy import), so we use `patch.dict('sys.modules')` to inject mock modules that get imported at runtime.

## Running Tests

### Using the Helper Script
```bash
# Basic usage
python3 run_tests.py

# With coverage
python3 run_tests.py --coverage

# HTML coverage report
python3 run_tests.py --html

# Verbose output
python3 run_tests.py -v

# Specific test file
python3 run_tests.py tests/test_fit_editor.py

# Specific test
python3 run_tests.py tests/test_fit_editor.py::TestFitEditor::test_edit_tpv_fit_file

# Combined options
python3 run_tests.py --coverage --html -v
```

### Using pytest Directly
```bash
# Run all tests
uv run pytest tests/

# With coverage
uv run pytest tests/ --cov=fit_file_faker --cov-report=html

# Verbose
uv run pytest tests/ -v
```

## Continuous Integration

The test suite runs automatically on GitHub Actions for:
- **Python versions**: 3.12, 3.13, 3.14
- **Operating systems**: Ubuntu, macOS, Windows
- **Triggers**: Push to main/develop/refactor branches, pull requests

Workflow file: `.github/workflows/test.yml`

Coverage reports are uploaded to Codecov on successful Ubuntu + Python 3.12 runs.

## Test Files

```
tests/
├── __init__.py                 # Package marker
├── conftest.py                 # Shared fixtures and configuration
├── test_fit_editor.py          # FIT editing tests
├── test_config.py              # Configuration tests
├── test_app.py                 # Application and upload tests
├── README.md                   # Detailed test documentation
└── files/                      # Test FIT files
    ├── tpv_20250111.fit
    ├── zwift_20250401.fit
    ├── mywhoosh_20260111.fit
    ├── karoo_20251119.fit
    └── coros_20251118.fit
```

## Adding New Tests

When adding support for a new platform:

1. Add the FIT file to `tests/files/` (make sure to sanitize it of any personally identifiable in formation)
2. Create a fixture in `conftest.py`:
   ```python
   @pytest.fixture
   def new_platform_fit_file(test_files_dir):
       return test_files_dir / "new_platform.fit"
   ```
3. Add a test in `test_fit_editor.py`:
   ```python
   def test_edit_new_platform_fit_file(self, fit_editor, new_platform_fit_file, temp_dir):
       output_file = temp_dir / "new_platform_modified.fit"
       result = fit_editor.edit_fit(new_platform_fit_file, output=output_file)
       
       assert result == output_file
       assert output_file.exists()
       
       # Verify modifications
       modified_fit = FitFile.from_file(str(output_file))
       for record in modified_fit.records:
           if isinstance(record.message, FileIdMessage):
               assert record.message.manufacturer == Manufacturer.GARMIN.value
   ```

## Test Coverage

**Current coverage: 100%** for all production code (`fit_file_faker.config` and `fit_file_faker.app`).

Coverage includes:
- ✅ File reading and parsing
- ✅ Manufacturer/device modification
- ✅ Configuration management (all paths, including edge cases)
- ✅ Upload functionality (mocked Garmin Connect)
- ✅ Error handling (HTTP errors, invalid input, keyboard interrupts)
- ✅ CLI interface (all argument combinations)
- ✅ Interactive prompts (questionary mocking)
- ✅ Platform-specific code (macOS, Windows, Linux)

Run `python3 run_tests.py --html` to generate a detailed HTML coverage report.

## Troubleshooting

### Tests fail with config errors
- Ensure `isolate_config_dirs` fixture is present in `conftest.py`
- Check that tests don't bypass fixtures to access real directories

### Garth import errors
- Verify `sys.modules` patching is used for garth tests
- Ensure mock garth module has all required attributes (`.client`, `.resume`, etc.)

### FIT file not found
- Check that test files exist in `tests/files/`
- Verify fixture names match file names

### Permission errors
- Run tests from the project root directory
- Ensure test files have read permissions

## Best Practices

1. **Always use fixtures** for test data (don't hardcode paths)
2. **Mock external services** (no real network calls)
3. **Use temp directories** for output files
4. **Test both success and failure** paths
5. **Keep tests independent** (no shared state)
6. **Use descriptive test names** that explain what's being tested
7. **Verify behavior, not implementation** (test outcomes, not internals)

## Resources

- Full test documentation: `tests/README.md`
- pytest documentation: [https://docs.pytest.org/](https://docs.pytest.org/)
- pytest-cov documentation: [https://pytest-cov.readthedocs.io/](https://pytest-cov.readthedocs.io/)
- GitHub Actions workflow: `.github/workflows/test.yml`
