"""
Tests for configuration management functionality.
"""

import json
import logging
from pathlib import Path

import pytest
import questionary

from fit_file_faker.config import (
    Config,
    ConfigManager,
    get_fitfiles_path,
    get_tpv_folder,
)

# Import shared mock classes from conftest
from .conftest import MockQuestion


# Test Fixtures and Helpers


@pytest.fixture
def mock_questionary_basic(monkeypatch):
    """Mock questionary with basic return values for text/password inputs."""

    def mock_text(prompt):
        return MockQuestion("")

    def mock_password(prompt):
        return MockQuestion("")

    monkeypatch.setattr(questionary, "text", mock_text)
    monkeypatch.setattr(questionary, "password", mock_password)


@pytest.fixture
def mock_get_fitfiles_path(monkeypatch):
    """Mock get_fitfiles_path to return a test path."""

    def _mock(*args, **kwargs):
        return Path("/mocked/fitfiles/path")

    monkeypatch.setattr("fit_file_faker.config.get_fitfiles_path", _mock)
    return _mock


@pytest.fixture
def mock_get_tpv_folder(monkeypatch):
    """Mock get_tpv_folder to return a test path."""

    def _mock(existing_path):
        return Path("/mocked/tpv/folder")

    monkeypatch.setattr("fit_file_faker.config.get_tpv_folder", _mock)
    return _mock


@pytest.fixture
def config_with_all_fields():
    """Create a Config with all fields populated."""
    return Config(
        garmin_username="test@example.com",
        garmin_password="password123",
        fitfiles_path=Path("/path/to/fitfiles"),
    )


class TestConfig:
    """Tests for the Config dataclass."""

    def test_config_initialization(self):
        """Test Config initialization with default and provided values."""
        # Test defaults
        config = Config()
        assert config.garmin_username is None
        assert config.garmin_password is None
        assert config.fitfiles_path is None

        # Test with values
        config = Config(
            garmin_username="test@example.com",
            garmin_password="password123",
            fitfiles_path=Path("/path/to/fitfiles"),
        )
        assert config.garmin_username == "test@example.com"
        assert config.garmin_password == "password123"
        assert config.fitfiles_path == Path("/path/to/fitfiles")


class TestConfigManager:
    """Tests for the ConfigManager class."""

    def test_config_manager_initialization(self):
        """Test ConfigManager initialization creates config file with defaults."""
        config_manager = ConfigManager()

        # Config file should exist
        assert config_manager.config_file.exists()
        # Config should be initialized with None values
        assert isinstance(config_manager.config, Config)
        assert config_manager.config.garmin_username is None
        assert config_manager.config.garmin_password is None
        assert config_manager.config.fitfiles_path is None

    def test_load_config_with_data(self, tmp_path):
        """Test loading config from file with data."""
        # Create config file with data
        config_file = tmp_path / "config" / ".config.json"
        config_data = {
            "garmin_username": "user@example.com",
            "garmin_password": "secret",
            "fitfiles_path": "/path/to/files",
        }
        with config_file.open("w") as f:
            json.dump(config_data, f)

        # Load config
        config_manager = ConfigManager()

        assert config_manager.config.garmin_username == "user@example.com"
        assert config_manager.config.garmin_password == "secret"
        assert config_manager.config.fitfiles_path == "/path/to/files"

    def test_save_config(self):
        """Test saving config to file with string and Path object serialization."""
        config_manager = ConfigManager()

        # Test with string path
        config_manager.config.garmin_username = "test@example.com"
        config_manager.config.garmin_password = "password"
        config_manager.config.fitfiles_path = "/test/path"
        config_manager.save_config()

        with config_manager.config_file.open("r") as f:
            data = json.load(f)
        assert data["garmin_username"] == "test@example.com"
        assert data["garmin_password"] == "password"
        assert data["fitfiles_path"] == "/test/path"

        # Test with Path object - should serialize to string
        config_manager.config.fitfiles_path = Path("/path/to/fitfiles")
        config_manager.save_config()

        with config_manager.config_file.open("r") as f:
            data = json.load(f)
        # Use Path.as_posix() to handle cross-platform path comparison
        assert Path(data["fitfiles_path"]).as_posix() == "/path/to/fitfiles"
        assert isinstance(data["fitfiles_path"], str)

    def test_is_valid(self):
        """Test is_valid method with various scenarios."""
        config_manager = ConfigManager()

        # All fields present - should be valid
        config_manager.config.garmin_username = "test@example.com"
        config_manager.config.garmin_password = "password"
        config_manager.config.fitfiles_path = Path("/path/to/files")
        assert config_manager.is_valid() is True
        assert config_manager.is_valid(excluded_keys=None) is True

        # Missing field - should be invalid
        config_manager.config.fitfiles_path = None
        assert config_manager.is_valid() is False

        # Missing field but excluded - should be valid
        assert config_manager.is_valid(excluded_keys=["fitfiles_path"]) is True

    def test_get_config_file_path(self, tmp_path):
        """Test getting config file path."""
        config_manager = ConfigManager()

        config_path = config_manager.get_config_file_path()

        assert isinstance(config_path, Path)
        assert config_path.name == ".config.json"
        assert config_path.parent == tmp_path / "config"

    def test_build_config_file_interactive(self, monkeypatch, mock_get_fitfiles_path):
        """Test interactive config file building."""
        config_manager = ConfigManager()

        # Mock questionary inputs
        def mock_text(prompt):
            return MockQuestion(
                "interactive@example.com" if "garmin_username" in prompt else ""
            )

        def mock_password(prompt):
            return MockQuestion("interactive_pass")

        monkeypatch.setattr(questionary, "text", mock_text)
        monkeypatch.setattr(questionary, "password", mock_password)

        # Build config
        config_manager.build_config_file(rewrite_config=False, excluded_keys=[])

        assert config_manager.config.garmin_username == "interactive@example.com"
        assert config_manager.config.garmin_password == "interactive_pass"
        # Use Path.as_posix() to handle cross-platform path comparison
        assert (
            Path(str(config_manager.config.fitfiles_path)).as_posix()
            == "/mocked/fitfiles/path"
        )

    def test_build_config_file_with_existing_values(self, mock_get_fitfiles_path):
        """Test that existing values are preserved when not overwriting."""
        config_manager = ConfigManager()

        # Set existing values
        config_manager.config.garmin_username = "existing@example.com"
        config_manager.config.garmin_password = "existing_pass"
        config_manager.save_config()

        # Reload config manager
        config_manager = ConfigManager()

        # Build without overwriting
        config_manager.build_config_file(
            overwrite_existing_vals=False, rewrite_config=False, excluded_keys=[]
        )

        # Existing values should be preserved
        assert config_manager.config.garmin_username == "existing@example.com"
        assert config_manager.config.garmin_password == "existing_pass"

    def test_build_config_file_hides_password_in_prompt(
        self, monkeypatch, mock_get_fitfiles_path
    ):
        """Test that password is masked with <**hidden**> in interactive prompts."""
        config_manager = ConfigManager()

        # Set existing password
        config_manager.config.garmin_username = "test@example.com"
        config_manager.config.garmin_password = "secret_password_123"
        config_manager.config.fitfiles_path = Path("/path/to/files")
        config_manager.save_config()

        # Reload to get fresh instance
        config_manager = ConfigManager()

        # Track what prompt message was passed to questionary
        captured_prompts = []

        def mock_text(prompt):
            captured_prompts.append(prompt)
            return MockQuestion("")

        def mock_password(prompt):
            captured_prompts.append(prompt)
            return MockQuestion("")

        monkeypatch.setattr(questionary, "text", mock_text)
        monkeypatch.setattr(questionary, "password", mock_password)

        # Build config with overwrite enabled to trigger prompts for existing values
        config_manager.build_config_file(
            overwrite_existing_vals=True, rewrite_config=False, excluded_keys=[]
        )

        # Find the password prompt and verify masking
        password_prompts = [p for p in captured_prompts if "garmin_password" in p]
        assert len(password_prompts) > 0
        for prompt in password_prompts:
            assert "secret_password_123" not in prompt
            assert "<**hidden**>" in prompt

    def test_build_config_file_warns_on_invalid_input(
        self, monkeypatch, caplog, mock_get_fitfiles_path
    ):
        """Test that warning is logged when user provides invalid (empty) input."""
        config_manager = ConfigManager()
        config_manager.config.garmin_username = None
        config_manager.config.garmin_password = "password"
        config_manager.config.fitfiles_path = Path("/path/to/files")

        # Track number of times questionary is called
        call_count = {"text": 0}

        def mock_text(prompt):
            call_count["text"] += 1
            # First call returns empty (invalid), second returns valid
            return MockQuestion("" if call_count["text"] == 1 else "valid@example.com")

        monkeypatch.setattr(questionary, "text", mock_text)
        monkeypatch.setattr(questionary, "password", lambda p: MockQuestion(""))

        # Build config
        with caplog.at_level(logging.WARNING):
            config_manager.build_config_file(
                overwrite_existing_vals=True, rewrite_config=False, excluded_keys=[]
            )

        # Verify warning was logged and valid value was eventually set
        assert any(
            "Entered input was not valid, please try again" in record.message
            for record in caplog.records
        )
        assert config_manager.config.garmin_username == "valid@example.com"

    def test_build_config_file_keyboard_interrupt(self, monkeypatch, caplog):
        """Test that KeyboardInterrupt is handled properly during config building."""
        config_manager = ConfigManager()
        config_manager.config.garmin_username = None
        config_manager.config.garmin_password = "password"
        config_manager.config.fitfiles_path = Path("/path/to/files")

        # Mock to raise KeyboardInterrupt
        def mock_text(prompt):
            class MockQuestion:
                def unsafe_ask(self):
                    raise KeyboardInterrupt()

            return MockQuestion()

        monkeypatch.setattr(questionary, "text", mock_text)

        # Should exit with code 1 when interrupted
        with pytest.raises(SystemExit) as exc_info:
            with caplog.at_level(logging.ERROR):
                config_manager.build_config_file(
                    overwrite_existing_vals=True, rewrite_config=False, excluded_keys=[]
                )

        assert exc_info.value.code == 1
        assert any(
            "User canceled input; exiting!" in record.message
            for record in caplog.records
        )

    def test_build_config_file_excluded_keys_none_handling(
        self, mock_questionary_basic, mock_get_fitfiles_path
    ):
        """Test that excluded_keys=None is properly converted to empty list (covers lines 88-89)."""
        config_manager = ConfigManager()
        config_manager.config.garmin_username = "test@example.com"
        config_manager.config.garmin_password = "password"
        config_manager.config.fitfiles_path = Path("/path/to/files")

        # Call with excluded_keys=None explicitly - should not raise any errors
        # This tests the line: if excluded_keys is None: excluded_keys = []
        config_manager.build_config_file(
            overwrite_existing_vals=False,
            rewrite_config=False,
            excluded_keys=None,  # Explicitly pass None
        )

        # Config should remain intact
        assert config_manager.config.garmin_username == "test@example.com"

    def test_build_config_file_rewrite_config(
        self, mock_questionary_basic, mock_get_fitfiles_path
    ):
        """Test rewrite_config parameter controls whether config is saved to file."""
        # Test rewrite_config=True saves changes
        config_manager = ConfigManager()
        config_manager.config.garmin_username = "test@example.com"
        config_manager.config.garmin_password = "password"
        config_manager.config.fitfiles_path = Path("/path/to/files")

        config_manager.build_config_file(
            overwrite_existing_vals=False, rewrite_config=True, excluded_keys=[]
        )

        with config_manager.config_file.open("r") as f:
            saved_data = json.load(f)
        assert saved_data["garmin_username"] == "test@example.com"
        assert saved_data["garmin_password"] == "password"

        # Test rewrite_config=False does NOT save changes
        config_manager2 = ConfigManager()
        config_manager2.config.garmin_username = "original@example.com"
        config_manager2.config.garmin_password = "original_password"
        config_manager2.config.fitfiles_path = Path("/original/path")
        config_manager2.save_config()

        with config_manager2.config_file.open("r") as f:
            original_data = json.load(f)

        # Update in memory only
        config_manager2.config.garmin_username = "updated@example.com"
        config_manager2.build_config_file(
            overwrite_existing_vals=False, rewrite_config=False, excluded_keys=[]
        )

        # File should still have original data
        with config_manager2.config_file.open("r") as f:
            current_data = json.load(f)
        assert current_data == original_data
        assert current_data["garmin_username"] == "original@example.com"


class TestGetFitfilesPath:
    """Tests for the get_fitfiles_path function."""

    @pytest.fixture
    def tpv_path_with_user(self, tmp_path):
        """Create TPVirtual directory with a valid user folder."""
        tpv_path = tmp_path / "TPVirtual"
        tpv_path.mkdir()
        user_folder = tpv_path / "a1b2c3d4e5f6g7h8"  # 16 alphanumeric chars
        user_folder.mkdir()
        fit_folder = user_folder / "FITFiles"
        fit_folder.mkdir()
        return tpv_path, fit_folder

    def test_get_fitfiles_path_no_user_folders(self, tmp_path, monkeypatch, caplog):
        """Test error when no TPVirtual user folders are found."""
        # Create empty TPVirtual directory
        tpv_path = tmp_path / "TPVirtual"
        tpv_path.mkdir()

        monkeypatch.setattr("fit_file_faker.config.get_tpv_folder", lambda x: tpv_path)

        # Should exit when no user folders found
        with pytest.raises(SystemExit) as exc_info:
            with caplog.at_level(logging.ERROR):
                get_fitfiles_path(None)

        assert exc_info.value.code == 1
        assert any(
            "Cannot find a TP Virtual User folder" in record.message
            for record in caplog.records
        )

    def test_get_fitfiles_path_single_folder(
        self, monkeypatch, caplog, tpv_path_with_user
    ):
        """Test with single user folder - both confirmed and rejected scenarios."""
        tpv_path, fit_folder = tpv_path_with_user
        monkeypatch.setattr("fit_file_faker.config.get_tpv_folder", lambda x: tpv_path)

        # Test user confirms folder
        monkeypatch.setattr(
            questionary, "select", lambda t, choices: MockQuestion("yes")
        )
        with caplog.at_level(logging.INFO):
            result = get_fitfiles_path(None)
        assert result == fit_folder
        assert any(
            "Found TP Virtual User directory" in r.message for r in caplog.records
        )

        # Test user rejects folder
        caplog.clear()
        monkeypatch.setattr(
            questionary, "select", lambda t, choices: MockQuestion("no")
        )
        with pytest.raises(SystemExit) as exc_info:
            with caplog.at_level(logging.ERROR):
                get_fitfiles_path(None)
        assert exc_info.value.code == 1
        assert any(
            "Failed to find correct TP Virtual User folder" in r.message
            for r in caplog.records
        )

    def test_get_fitfiles_path_multiple_folders(self, tmp_path, monkeypatch, caplog):
        """Test with multiple user folders and user selects one."""
        tpv_path = tmp_path / "TPVirtual"
        tpv_path.mkdir()
        user_folder1 = tpv_path / "a1b2c3d4e5f6g7h8"
        user_folder2 = tpv_path / "z9y8x7w6v5u4t3s2"
        user_folder1.mkdir()
        user_folder2.mkdir()
        fit_folder2 = user_folder2 / "FITFiles"
        (user_folder1 / "FITFiles").mkdir()
        fit_folder2.mkdir()

        monkeypatch.setattr("fit_file_faker.config.get_tpv_folder", lambda x: tpv_path)
        monkeypatch.setattr(
            questionary, "select", lambda t, choices: MockQuestion("z9y8x7w6v5u4t3s2")
        )

        with caplog.at_level(logging.INFO):
            result = get_fitfiles_path(None)

        assert result == fit_folder2
        assert any(
            "Found TP Virtual User directory" in r.message for r in caplog.records
        )

    def test_get_fitfiles_path_ignores_non_matching_folders(
        self, tmp_path, monkeypatch
    ):
        """Test that folders not matching the 16-char pattern are ignored."""
        tpv_path = tmp_path / "TPVirtual"
        tpv_path.mkdir()
        valid_folder = tpv_path / "a1b2c3d4e5f6g7h8"
        valid_folder.mkdir()
        (tpv_path / "too_short").mkdir()
        (tpv_path / "this_is_too_long_folder").mkdir()
        (tpv_path / "has-special-chars").mkdir()
        fit_folder = valid_folder / "FITFiles"
        fit_folder.mkdir()

        monkeypatch.setattr("fit_file_faker.config.get_tpv_folder", lambda x: tpv_path)
        monkeypatch.setattr(
            questionary, "select", lambda t, choices: MockQuestion("yes")
        )

        result = get_fitfiles_path(None)
        assert result == fit_folder  # Should only find the valid folder


class TestGetTpvFolder:
    """Tests for the get_tpv_folder function."""

    def test_get_tpv_folder_from_environment(self, monkeypatch, caplog):
        """Test that TPV_DATA_PATH environment variable is used when set."""
        test_path = "/custom/tpv/path"
        monkeypatch.setenv("TPV_DATA_PATH", test_path)

        with caplog.at_level(logging.INFO):
            result = get_tpv_folder(None)

        assert result == Path(test_path)
        assert any(
            f'Using TPV_DATA_PATH value read from the environment: "{test_path}"'
            in r.message
            for r in caplog.records
        )

    def test_get_tpv_folder_platform_defaults(self, monkeypatch):
        """Test default paths on different platforms."""
        monkeypatch.delenv("TPV_DATA_PATH", raising=False)

        # macOS
        monkeypatch.setattr("sys.platform", "darwin")
        assert get_tpv_folder(None) == Path.home() / "TPVirtual"

        # Windows
        monkeypatch.setattr("sys.platform", "win32")
        assert get_tpv_folder(None) == Path.home() / "Documents" / "TPVirtual"

    def test_get_tpv_folder_linux_manual_entry(self, monkeypatch, caplog):
        """Test manual path entry on Linux with and without default path."""
        monkeypatch.delenv("TPV_DATA_PATH", raising=False)
        monkeypatch.setattr("sys.platform", "linux")
        user_path = "/home/user/TPVirtual"

        # Test with default path
        monkeypatch.setattr(
            questionary, "path", lambda p, default="": MockQuestion(user_path)
        )
        with caplog.at_level(logging.WARNING):
            result = get_tpv_folder(Path("/home/user/default/path"))
        assert result == Path(user_path)
        assert any(
            "TrainingPeaks Virtual user folder can only be automatically detected on Windows and OSX"
            in r.message
            for r in caplog.records
        )

        # Test without default path (verifies default="" is used)
        caplog.clear()

        def mock_path_verify_default(prompt, default=""):
            assert default == ""  # Verify default is empty when None passed
            return MockQuestion(user_path)

        monkeypatch.setattr(questionary, "path", mock_path_verify_default)
        with caplog.at_level(logging.WARNING):
            result = get_tpv_folder(None)
        assert result == Path(user_path)

    def test_get_tpv_folder_environment_overrides_platform(self, monkeypatch):
        """Test that environment variable takes precedence over platform detection."""
        test_path = "/env/override/path"
        monkeypatch.setenv("TPV_DATA_PATH", test_path)
        monkeypatch.setattr("sys.platform", "darwin")

        result = get_tpv_folder(None)

        # Should use environment variable, not ~/TPVirtual
        assert result == Path(test_path)
        assert result != Path.home() / "TPVirtual"
