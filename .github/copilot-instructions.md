# Fit File Faker - AI Coding Guidelines

## Project Overview
This is a Python CLI tool that modifies FIT files from virtual cycling platforms (TrainingPeaks Virtual, Zwift, etc.) to appear as Garmin Edge 830 recordings, then uploads them to Garmin Connect. The tool enables Training Effect calculations and badge unlocks that Garmin Connect normally reserves for Garmin devices.

## Architecture
- **Entry point**: `fit_file_faker/app.py:run()` (CLI script: `fit-file-faker`)
- **Core logic**: FIT file manipulation using Stages Cycling's `fit_tool` library
- **Authentication**: OAuth via `garth` library with token caching in `~/.cache/fit-file-faker/.garth/`
- **Configuration**: JSON config in platform-specific user config directory (e.g., `~/.config/fit-file-faker/.config.json`)

## Key Components
- `fit_file_faker/app.py`: Main application with file editing, uploading, and monitoring logic
- `fit_file_faker/config.py`: Configuration management and validation
- `fit_file_faker/cli.py`: CLI entrypoint (under refactoring)

## Critical Patterns

### FIT File Modification
**Always modify these manufacturer IDs to Garmin (1) with Edge 830 product (3122):**
- `Manufacturer.DEVELOPMENT.value` (255)
- `Manufacturer.ZWIFT.value` (32)
- `Manufacturer.WAHOO_FITNESS.value` (32)
- `Manufacturer.PEAKSWARE.value` (3)
- `Manufacturer.HAMMERHEAD.value` (6)

**Example from `app.py:165-175`:**
```python
if (
    m.manufacturer == Manufacturer.DEVELOPMENT.value
    or m.manufacturer == Manufacturer.ZWIFT.value
    or m.manufacturer == Manufacturer.WAHOO_FITNESS.value
    or m.manufacturer == Manufacturer.PEAKSWARE.value
    or m.manufacturer == Manufacturer.HAMMERHEAD.value
):
    new_m.manufacturer = Manufacturer.GARMIN.value
    new_m.product = GarminProduct.EDGE_830.value
```

### File Processing Flow
1. Parse FIT file with `FitFile.from_file()`
2. Iterate through records, modifying `FileIdMessage` and `DeviceInfoMessage` records
3. Add `FileCreatorMessage` with specific software/hardware versions (975/255)
4. Rebuild file with `FitFileBuilder` and save

### Upload Logic
- Use `garth.login()` for initial auth, `garth.resume()` for subsequent runs
- Store OAuth tokens in user cache directory via `platformdirs`
- Handle HTTP 409 conflicts (duplicate activities) gracefully

### Directory Monitoring
- Use `watchdog.Observer` to watch for new `.fit` files
- Sleep 5 seconds after detection to ensure file is fully written
- Track processed files in `.uploaded_files.json` to avoid duplicates

## Development Workflow

### Setup
```bash
git clone <repo>
cd fit-file-faker
uv sync  # Install dependencies
```

### Testing
- Use `--dryrun` flag for safe testing without file modifications or uploads
- Test with sample FIT files from supported platforms
- Verify Garmin Connect rejects actual duplicates (HTTP 409)

### Building & Publishing
- `uv build` creates distribution packages
- GitHub Actions publishes to PyPI on tagged releases
- Uses trusted publishing with OIDC tokens

## Code Style & Conventions

### Logging
- Use Rich logging with markup support
- Debug level shows detailed FIT record modifications
- Info level for user-facing progress messages
- Warning/Error for issues and failures

### Error Handling
- Check Python version >= 3.12.0 at startup
- Validate config before operations
- Graceful handling of missing FIT files or invalid formats
- Interactive config setup with `questionary` prompts

### File Paths
- Use `pathlib.Path` throughout
- Resolve to absolute paths for reliability
- Platform-specific paths via `platformdirs` (config: user_config_dir, cache: user_cache_path)

### Dependencies
- Pin minimum versions in `pyproject.toml`
- Use `uv` for dependency management and virtual environments
- Group dev dependencies separately

## Common Pitfalls
- FIT files must be fully written before processing (watchdog sleep delay)
- Garmin rejects duplicate activities by timestamp
- OAuth tokens expire and require re-authentication
- Config file paths vary by platform (macOS: `~/Library/Application Support/`, Linux: `~/.config/`)

## Refactoring Notes
- Currently moving from monolithic `app.py` to modular `fit_file_faker/` package
- CLI logic being extracted to `cli.py`
- Maintain backward compatibility with existing config and behavior</content>
<parameter name="filePath">/Users/josh/git_repos/Fit-File-Faker/.github/copilot-instructions.md