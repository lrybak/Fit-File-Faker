"""
Pytest configuration and shared fixtures for Fit File Faker tests.
"""

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

# Apply monkey patch for COROS files before importing FitFile
from fit_file_faker.utils import apply_fit_tool_patch

apply_fit_tool_patch()

# Now import FitFile after the monkey patch
from fit_tool.fit_file import FitFile  # noqa: E402


# Auto-use fixture to isolate all tests from real config/cache directories
@pytest.fixture(autouse=True)
def isolate_config_dirs(monkeypatch, tmp_path):
    """
    Automatically patch platformdirs for ALL tests to use temporary directories.
    This prevents tests from touching real user config/cache directories.
    """
    config_dir = tmp_path / "config"
    cache_dir = tmp_path / "cache"
    config_dir.mkdir()
    cache_dir.mkdir()

    # Create a mock PlatformDirs class
    class MockPlatformDirs:
        def __init__(self, *args, **kwargs):
            self.user_config_path = config_dir
            self.user_cache_path = cache_dir

    # Patch platformdirs in both config and app modules
    monkeypatch.setattr("fit_file_faker.config.PlatformDirs", MockPlatformDirs)

    # Also ensure the dirs object is recreated with mocked PlatformDirs
    from fit_file_faker import config

    config.dirs = MockPlatformDirs("FitFileFaker", appauthor=False)

    # Recreate config_manager to use the mocked directories
    config.config_manager = config.ConfigManager()

    yield


@pytest.fixture(scope="module")
def test_files_dir():
    """Return the path to the test files directory."""
    return Path(__file__).parent / "files"


@pytest.fixture(scope="module")
def tpv_fit_file_0_4_7(test_files_dir):
    """
    Return path to TrainingPeaks Virtual test FIT file.

    This file was created by v0.4.7 of TPV on Jan 11, 2025
    """
    return test_files_dir / "tpv_20250111.fit"


@pytest.fixture(scope="module")
def tpv_fit_file_0_4_30(test_files_dir):
    """
    Return path to TrainingPeaks Virtual test FIT file.

    This file was created by v0.4.30 of TPV on Nov 20, 2025. This file
    includes the TPV "product indicator" added in v0.4.10 (see release
    notes: https://help.trainingpeaks.com/hc/en-us/articles/34924247758477-TrainingPeaks-Virtual-Release-Notes)
    """
    return test_files_dir / "tpv_20251120.fit"


@pytest.fixture(scope="module")
def zwift_fit_file(test_files_dir):
    """Return path to Zwift test FIT file."""
    return test_files_dir / "zwift_20250401.fit"


@pytest.fixture(scope="module")
def mywhoosh_fit_file(test_files_dir):
    """Return path to MyWhoosh test FIT file."""
    return test_files_dir / "mywhoosh_20260111.fit"


@pytest.fixture(scope="module")
def karoo_fit_file(test_files_dir):
    """Return path to Hammerhead Karoo test FIT file."""
    return test_files_dir / "karoo_20251119.fit"


@pytest.fixture(scope="module")
def coros_fit_file(test_files_dir):
    """Return path to COROS test FIT file."""
    return test_files_dir / "coros_20251118.fit"


@pytest.fixture(scope="module")
def all_test_fit_files(
    tpv_fit_file, zwift_fit_file, mywhoosh_fit_file, karoo_fit_file, coros_fit_file
):
    """Return all test FIT files."""
    return [
        tpv_fit_file,
        zwift_fit_file,
        mywhoosh_fit_file,
        karoo_fit_file,
        coros_fit_file,
    ]


# Parsed FIT file fixtures - function scoped for test isolation
@pytest.fixture
def tpv_fit_0_4_7_parsed(tpv_fit_file_0_4_7):
    """
    Return parsed TrainingPeaks Virtual FIT file.

    This file was created by v0.4.7 of TPV on Jan 11, 2025
    """
    return FitFile.from_file(str(tpv_fit_file_0_4_7))


@pytest.fixture(scope="module")
def tpv_fit_file(tpv_fit_file_0_4_30):
    """Return path to TrainingPeaks Virtual test FIT file."""
    return tpv_fit_file_0_4_30


@pytest.fixture
def tpv_fit_parsed(tpv_fit_file_0_4_30):
    """Return parsed TrainingPeaks Virtual FIT file."""
    return FitFile.from_file(str(tpv_fit_file_0_4_30))


@pytest.fixture
def tpv_fit_0_4_30_parsed(tpv_fit_file_0_4_30):
    """
    Return parsed TrainingPeaks Virtual FIT file.

    This file was created by v0.4.30 of TPV on Nov 20, 2025
    """
    return FitFile.from_file(str(tpv_fit_file_0_4_30))


@pytest.fixture
def zwift_fit_parsed(zwift_fit_file):
    """Return parsed Zwift FIT file."""
    return FitFile.from_file(str(zwift_fit_file))


@pytest.fixture
def mywhoosh_fit_parsed(mywhoosh_fit_file):
    """Return parsed MyWhoosh FIT file."""
    return FitFile.from_file(str(mywhoosh_fit_file))


@pytest.fixture
def karoo_fit_parsed(karoo_fit_file):
    """Return parsed Karoo FIT file."""
    return FitFile.from_file(str(karoo_fit_file))


@pytest.fixture
def coros_fit_parsed(coros_fit_file):
    """Return parsed COROS FIT file."""
    return FitFile.from_file(str(coros_fit_file))


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test outputs."""
    with TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_config_file(tmp_path):
    """Create a mock configuration file in the isolated config directory."""
    from fit_file_faker.config import config_manager

    config_manager.config.garmin_username = "test_user@example.com"
    config_manager.config.garmin_password = "test_password"
    config_manager.config.fitfiles_path = str(tmp_path / "fitfiles")
    config_manager.save_config()

    return config_manager.config_file


# Shared Mock Classes and Fixtures


class MockQuestion:
    """Mock questionary question object for testing interactive prompts."""

    def __init__(self, return_value):
        self.return_value = return_value

    def ask(self):
        return self.return_value

    def unsafe_ask(self):
        return self.return_value


class MockGarthHTTPError(Exception):
    """Mock Garth HTTP error with configurable status code."""

    def __init__(self, status_code=500):
        from unittest.mock import MagicMock

        self.error = MagicMock()
        self.error.response.status_code = status_code


class MockGarthException(Exception):
    """Mock Garth exception for testing authentication flows."""

    pass


@pytest.fixture
def mock_garth_basic():
    """Create basic mock garth module with successful operations."""
    from unittest.mock import MagicMock, Mock

    mock_garth = MagicMock()
    mock_garth_exc = MagicMock()

    mock_garth_exc.GarthException = MockGarthException
    mock_garth_exc.GarthHTTPError = MockGarthHTTPError

    mock_garth.resume.return_value = None
    mock_garth.client.username = "test_user"
    mock_garth.client.upload = Mock()

    return mock_garth, mock_garth_exc


@pytest.fixture
def mock_garth_with_login(mock_garth_basic):
    """Create mock garth that requires login."""
    mock_garth, mock_garth_exc = mock_garth_basic

    mock_garth.resume.side_effect = MockGarthException("Session expired")
    mock_garth.login.return_value = None
    mock_garth.save.return_value = None

    return mock_garth, mock_garth_exc
