# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Fit File Faker is a Python tool that modifies FIT (Flexible and Interoperable Data Transfer) files to make them appear as if they came from a Garmin Edge 830 device. The primary use case is enabling Garmin Connect's "Training Effect" calculations for activities from non-Garmin sources like TrainingPeaks Virtual (formerly indieVelo), Zwift, and other cycling platforms.

The tool is distributed as a single-file Python application (`app.py`) packaged via PyPI as `fit-file-faker`.

## Commands

### Development Setup
```bash
# Install dependencies with uv (preferred)
uv sync

# Or use pip in a virtual environment
python -m venv .venv
source .venv/bin/activate
pip install .
```

### Build and Distribution
```bash
# Build the package
uv build

# Install locally for testing
pip install -e .
```

### Running the Tool
```bash
# Show help
fit-file-faker -h

# Initial configuration (interactive)
fit-file-faker -s

# Edit a single FIT file
fit-file-faker path/to/file.fit

# Edit and upload to Garmin Connect
fit-file-faker -u path/to/file.fit

# Upload all new files in configured directory
fit-file-faker -ua

# Monitor directory for new files
fit-file-faker -m

# Dry run (no changes or uploads)
fit-file-faker -d path/to/file.fit
```

### Linting
```bash
# Run ruff (configured in dev dependencies)
ruff check .
ruff format .
```

## Architecture

### Single-File Design
The entire application is contained in `app.py` (~669 lines). This is intentional and should be preserved. The monolithic structure simplifies distribution and installation via PyPI.

### Core Workflow
1. **Read FIT file**: Uses the `fit_tool` library to parse binary FIT files
2. **Identify device messages**: Locates `FileIdMessage`, `FileCreatorMessage`, and `DeviceInfoMessage` records
3. **Rewrite manufacturer/product IDs**: Changes manufacturer codes from DEVELOPMENT (255), ZWIFT, WAHOO_FITNESS, PEAKSWARE, HAMMERHEAD, or MYWHOOSH (331) to GARMIN (1) with Edge 830 product ID (3122)
4. **Rebuild FIT file**: Uses `FitFileBuilder` to reconstruct the file with modified messages
5. **Upload (optional)**: Authenticates to Garmin Connect via `garth` library and uploads the modified file

### Key Components

**Configuration (`Config` dataclass)**
- Stored in platform-specific user config directory (via `platformdirs`)
- Contains: `garmin_username`, `garmin_password`, `fitfiles_path`
- Persisted as `.config.json`

**FIT File Processing**
- `edit_fit()`: Main function that reads, modifies, and saves FIT files
- `rewrite_file_id_message()`: Converts FileIdMessage to Garmin format
- Device info messages are similarly rewritten to Garmin Edge 830
- Preserves activity data (records, laps, sessions) - only modifies device metadata

**Upload Mechanism**
- Uses `garth` library for Garmin Connect OAuth authentication
- Credentials cached in platform-specific cache directory (`.garth` folder)
- Handles HTTP 409 conflicts (duplicate activities) gracefully

**Batch Processing**
- `upload_all()`: Processes all FIT files in a directory
- Maintains `.uploaded_files.json` to track processed files
- Creates temporary files for uploads (discarded after upload)

**Monitor Mode**
- Uses `watchdog` library with `PollingObserver`
- Watches for new `.fit` files in configured directory
- 5-second delay after file creation to ensure write completion (TrainingPeaks Virtual may still be writing)
- Automatically processes and uploads new files

### Supported Source Platforms
The tool recognizes and modifies FIT files from:
- TrainingPeaks Virtual (manufacturer: DEVELOPMENT or PEAKSWARE)
- Zwift (manufacturer: ZWIFT)
- Wahoo devices (manufacturer: WAHOO_FITNESS)
- Hammerhead Karoo (manufacturer: HAMMERHEAD)
- MyWhoosh (manufacturer code: 331, not in fit_tool's enum)

### Logging and Output
- Uses `rich` library for formatted console output
- `RichHandler` for colored, timestamped logs
- Custom `FitFileLogFilter` to suppress fit_tool's "actual:" warnings
- Debug mode (`-v`) provides detailed message-by-message processing logs

## Important Implementation Notes

### FIT File Structure
- FIT files contain a series of messages (records)
- Each data message must be preceded by a definition message
- When rewriting messages, always write: `DefinitionMessage.from_data_message(message)` then the message itself
- `FitFileBuilder(auto_define=True)` handles definition messages automatically when `add()` is called

### Edge 830 Simulation
The tool specifically emulates a Garmin Edge 830 with these values:
- Manufacturer: 1 (GARMIN)
- Product: 3122 (EDGE_830)
- Software version: 975 (in FileCreatorMessage)
- Hardware version: 255

### File Naming Convention
Modified files are saved as `{original_stem}_modified.fit` unless uploading in batch mode (which uses temp files).

### Platform Detection
The tool auto-detects TrainingPeaks Virtual user directories on:
- macOS: `~/TPVirtual`
- Windows: `~/Documents/TPVirtual`
- Linux: Prompts user for path (no auto-detection)

Override with `TPV_DATA_PATH` environment variable.

## Testing Strategy

The CI pipeline (`.github/workflows/install.yml`) tests on:
- Python 3.12 and 3.13
- Ubuntu, macOS, Windows

The test is minimal: install the package and run `fit-file-faker -h`. There are no unit tests currently.

When making changes, manually test with real FIT files from supported platforms. The `-d` (dryrun) flag is useful for testing without creating files or uploading.

## Release Process

Releases are automated via `.github/workflows/publish_and_release.yml`:
1. All pushes build the package and publish to TestPyPI
2. Tag pushes (e.g., `v1.2.3`) trigger PyPI publication and GitHub Release creation
3. Version is defined in `pyproject.toml` and must be manually updated before tagging

To release a new version:
1. Update version in `pyproject.toml`
2. Commit and push
3. Create and push a git tag: `git tag v1.2.4 && git push origin v1.2.4`
