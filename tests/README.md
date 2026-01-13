# Fit File Faker Test Suite

For comprehensive testing documentation, please see **[TESTING.md](../TESTING.md)** in the root directory.

## Quick Reference

### Run All Tests
```bash
# Using helper script (recommended)
python3 run_tests.py

# With coverage
python3 run_tests.py --html

# Using pytest directly
uv run pytest tests/
```

### Test Files
- `test_fit_editor.py` - FIT file editing tests (15 tests)
- `test_config.py` - Configuration management tests (21 tests, 100% coverage)
- `test_app.py` - Application and upload tests (32 tests, 100% coverage)
- `conftest.py` - Shared fixtures and test configuration

### Key Features
- ✅ **100% code coverage** for config and app modules
- ✅ **53 total tests** covering all functionality
- ✅ **Shared fixtures** in conftest.py eliminate duplication
- ✅ **Complete isolation** from real user data and configuration
- ✅ **No network calls** - all external services mocked

For detailed information on:
- Test structure and organization
- Mocking strategies
- Adding new tests
- Troubleshooting
- Best practices

Please refer to **[TESTING.md](../TESTING.md)**.
