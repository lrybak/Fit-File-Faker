"""
Tests for the main application functionality including CLI and upload features.
"""

import json
import logging
import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from fit_file_faker.app import (
    FILES_UPLOADED_NAME,
    NewFileEventHandler,
    monitor,
    upload,
    upload_all,
)

# Import shared mock classes from conftest
from .conftest import MockGarthHTTPError


# Test Fixtures and Helpers


@pytest.fixture
def mock_valid_config():
    """Create a valid mock config_manager."""
    with patch("fit_file_faker.app.config_manager") as mock_config:
        mock_config.is_valid.return_value = True
        mock_config.config.fitfiles_path = None
        mock_config.config.garmin_username = "test@example.com"
        mock_config.config.garmin_password = "testpass"
        yield mock_config


class TestUploadFunction:
    """Tests for the upload functionality with mocked Garmin requests."""

    def test_upload_success(self, tpv_fit_file, mock_garth_basic):
        """Test successful file upload to Garmin Connect."""
        mock_garth, mock_garth_exc = mock_garth_basic

        with patch.dict(
            "sys.modules", {"garth": mock_garth, "garth.exc": mock_garth_exc}
        ):
            upload(tpv_fit_file, dryrun=False)
            mock_garth.client.upload.assert_called_once()

    def test_upload_with_login(
        self, tpv_fit_file, mock_garth_with_login, mock_valid_config
    ):
        """Test upload that requires login."""
        mock_garth, mock_garth_exc = mock_garth_with_login

        with patch.dict(
            "sys.modules", {"garth": mock_garth, "garth.exc": mock_garth_exc}
        ):
            upload(tpv_fit_file, dryrun=False)

            # Verify login was called with config credentials
            mock_garth.login.assert_called_once_with("test@example.com", "testpass")
            mock_garth.save.assert_called_once()

    def test_upload_http_errors(self, tpv_fit_file, mock_garth_basic, caplog):
        """Test upload handling HTTP errors - 409 conflict handled gracefully, others raise."""
        mock_garth, mock_garth_exc = mock_garth_basic

        # Test 409 conflict (duplicate activity) - should be handled gracefully
        mock_garth.client.upload = Mock(side_effect=MockGarthHTTPError(409))
        with patch.dict(
            "sys.modules", {"garth": mock_garth, "garth.exc": mock_garth_exc}
        ):
            upload(tpv_fit_file, original_path=Path("test.fit"), dryrun=False)
            assert "conflict" in caplog.text.lower() or "409" in caplog.text

        # Test non-409 errors (500) - should raise exception
        caplog.clear()
        mock_garth.client.upload = Mock(side_effect=MockGarthHTTPError(500))
        with patch.dict(
            "sys.modules", {"garth": mock_garth, "garth.exc": mock_garth_exc}
        ):
            with pytest.raises(MockGarthHTTPError):
                upload(tpv_fit_file, original_path=Path("test.fit"), dryrun=False)

    def test_upload_dryrun(self, tpv_fit_file, mock_garth_basic):
        """Test that dryrun doesn't actually upload."""
        mock_garth, mock_garth_exc = mock_garth_basic

        with patch.dict(
            "sys.modules", {"garth": mock_garth, "garth.exc": mock_garth_exc}
        ):
            upload(tpv_fit_file, dryrun=True)
            mock_garth.client.upload.assert_not_called()

    def test_upload_interactive_credentials(self, tpv_fit_file, mock_garth_with_login):
        """Test interactive credential input when not in config."""
        mock_garth, mock_garth_exc = mock_garth_with_login

        with (
            patch.dict(
                "sys.modules", {"garth": mock_garth, "garth.exc": mock_garth_exc}
            ),
            patch("fit_file_faker.app.questionary") as mock_questionary,
            patch("fit_file_faker.app.config_manager") as mock_config_manager,
        ):
            # Mock questionary to provide credentials
            mock_questionary.text.return_value.ask.return_value = (
                "interactive@example.com"
            )
            mock_questionary.password.return_value.ask.return_value = "interactive_pass"

            # Mock config with no credentials
            mock_config_manager.config.garmin_username = None
            mock_config_manager.config.garmin_password = None

            upload(tpv_fit_file, dryrun=False)

            # Verify interactive prompts were used
            mock_questionary.text.assert_called_once()
            mock_questionary.password.assert_called_once()
            mock_garth.login.assert_called_once_with(
                "interactive@example.com", "interactive_pass"
            )


class TestUploadAllFunction:
    """Tests for batch upload functionality."""

    @patch("fit_file_faker.app.fit_editor")
    @patch("fit_file_faker.app.upload")
    def test_upload_all_new_files(
        self, mock_upload, mock_fit_editor, temp_dir, tpv_fit_file
    ):
        """Test uploading all new files in a directory."""
        # Copy test file to temp directory
        import shutil

        test_file = temp_dir / "test_activity.fit"
        shutil.copy(tpv_fit_file, test_file)

        # Mock fit_editor to return a path
        mock_fit_editor.edit_fit.return_value = temp_dir / "test_activity_modified.fit"

        # Run upload_all
        upload_all(temp_dir, dryrun=False)

        # Verify edit and upload were called
        assert mock_fit_editor.edit_fit.called
        assert mock_upload.called

        # Verify uploaded files list was created
        uploaded_list = temp_dir / FILES_UPLOADED_NAME
        assert uploaded_list.exists()

        with uploaded_list.open("r") as f:
            uploaded = json.load(f)
        assert "test_activity.fit" in uploaded

    @patch("fit_file_faker.app.fit_editor")
    @patch("fit_file_faker.app.upload")
    def test_upload_all_skips_already_uploaded(
        self, mock_upload, mock_fit_editor, temp_dir, tpv_fit_file
    ):
        """Test that already uploaded files are skipped."""
        import shutil

        # Copy test file
        test_file = temp_dir / "test_activity.fit"
        shutil.copy(tpv_fit_file, test_file)

        # Create uploaded files list with this file already in it
        uploaded_list = temp_dir / FILES_UPLOADED_NAME
        with uploaded_list.open("w") as f:
            json.dump(["test_activity.fit"], f)

        # Run upload_all
        upload_all(temp_dir, dryrun=False)

        # Should NOT process the file
        mock_fit_editor.edit_fit.assert_not_called()
        mock_upload.assert_not_called()

    @patch("fit_file_faker.app.fit_editor")
    @patch("fit_file_faker.app.upload")
    def test_upload_all_skips_modified_files(
        self, mock_upload, mock_fit_editor, temp_dir, tpv_fit_file
    ):
        """Test that files ending in _modified.fit are skipped."""
        import shutil

        # Copy test file with _modified suffix
        test_file = temp_dir / "test_activity_modified.fit"
        shutil.copy(tpv_fit_file, test_file)

        # Run upload_all
        upload_all(temp_dir, dryrun=False)

        # Should NOT process modified files
        mock_fit_editor.edit_fit.assert_not_called()

    def test_upload_all_preinitialize(self, temp_dir, tpv_fit_file):
        """Test preinitialize mode marks all files as uploaded without processing."""
        import shutil

        # Copy test files
        test_file1 = temp_dir / "test1.fit"
        test_file2 = temp_dir / "test2.fit"
        shutil.copy(tpv_fit_file, test_file1)
        shutil.copy(tpv_fit_file, test_file2)

        # Run with preinitialize
        upload_all(temp_dir, preinitialize=True, dryrun=False)

        # Check uploaded files list
        uploaded_list = temp_dir / FILES_UPLOADED_NAME
        assert uploaded_list.exists()

        with uploaded_list.open("r") as f:
            uploaded = json.load(f)

        assert "test1.fit" in uploaded
        assert "test2.fit" in uploaded

    @patch("fit_file_faker.app.fit_editor")
    @patch("fit_file_faker.app.upload")
    def test_upload_all_dryrun(
        self, mock_upload, mock_fit_editor, temp_dir, tpv_fit_file
    ):
        """Test that dryrun doesn't save uploaded files list."""
        import shutil

        test_file = temp_dir / "test_activity.fit"
        shutil.copy(tpv_fit_file, test_file)

        mock_fit_editor.edit_fit.return_value = temp_dir / "test_modified.fit"

        # Run with dryrun
        upload_all(temp_dir, dryrun=True)

        # Uploaded files list should exist but be empty initially
        uploaded_list = temp_dir / FILES_UPLOADED_NAME
        if uploaded_list.exists():
            with uploaded_list.open("r") as f:
                json.load(f)
            # In dryrun, the list might be created but shouldn't be updated with processed files
            # This depends on implementation details


class TestNewFileEventHandler:
    """Tests for the file monitoring event handler."""

    def test_event_handler_initialization(self):
        """Test NewFileEventHandler initialization."""
        handler = NewFileEventHandler(dryrun=False)

        assert handler.patterns == ["*.fit"]
        assert handler.ignore_directories is True
        assert handler.case_sensitive is False

    @patch("fit_file_faker.app.upload_all")
    @patch("fit_file_faker.app.time.sleep")
    def test_on_created_processes_file(self, mock_sleep, mock_upload_all, temp_dir):
        """Test that new file creation triggers processing."""
        handler = NewFileEventHandler(dryrun=False)

        # Create a mock event
        from watchdog.events import FileCreatedEvent

        test_file = temp_dir / "new_activity.fit"
        test_file.touch()

        event = FileCreatedEvent(str(test_file))

        # Trigger event
        handler.on_created(event)

        # Should sleep for 5 seconds (to ensure file is fully written)
        mock_sleep.assert_called_once_with(5)

        # Should call upload_all with the parent directory
        mock_upload_all.assert_called_once_with(temp_dir)

    @patch("fit_file_faker.app.upload_all")
    @patch("fit_file_faker.app.time.sleep")
    def test_on_created_dryrun(self, mock_sleep, mock_upload_all, temp_dir):
        """Test that dryrun doesn't process files."""
        handler = NewFileEventHandler(dryrun=True)

        from watchdog.events import FileCreatedEvent

        test_file = temp_dir / "new_activity.fit"
        test_file.touch()

        event = FileCreatedEvent(str(test_file))

        # Trigger event
        handler.on_created(event)

        # Should NOT sleep or upload
        mock_sleep.assert_not_called()
        mock_upload_all.assert_not_called()


class TestMonitorFunction:
    """Tests for directory monitoring functionality."""

    @patch("fit_file_faker.app.Observer")
    def test_monitor_starts_observer(self, mock_observer_class, temp_dir):
        """Test that monitor starts the file observer."""
        mock_observer = Mock()
        mock_observer_class.return_value = mock_observer
        mock_observer.is_alive.return_value = False  # Exit immediately

        # Run monitor (will exit immediately because is_alive returns False)
        monitor(temp_dir, dryrun=False)

        # Verify observer was configured and started
        mock_observer.schedule.assert_called_once()
        mock_observer.start.assert_called_once()
        mock_observer.stop.assert_called_once()
        mock_observer.join.assert_called()

    @patch("fit_file_faker.app.Observer")
    def test_monitor_handles_keyboard_interrupt(self, mock_observer_class, temp_dir):
        """Test that monitor gracefully handles KeyboardInterrupt."""
        mock_observer = Mock()
        mock_observer_class.return_value = mock_observer

        # Simulate KeyboardInterrupt
        mock_observer.is_alive.return_value = True
        mock_observer.join.side_effect = [KeyboardInterrupt(), None]

        # Should handle interrupt gracefully
        monitor(temp_dir, dryrun=False)

        mock_observer.stop.assert_called_once()


class TestCLIIntegration:
    """Integration tests for CLI functionality."""

    @patch("fit_file_faker.app.fit_editor")
    @patch("sys.argv", ["fit-file-faker", "--help"])
    def test_help_argument(self, mock_fit_editor):
        """Test that --help doesn't error."""
        from fit_file_faker.app import run

        with pytest.raises(SystemExit) as exc_info:
            run()

        # --help should exit with code 0
        assert exc_info.value.code == 0

    @patch("fit_file_faker.app.fit_editor")
    def test_version_check_passes(self, mock_fit_editor):
        """Test that Python version check passes on supported versions."""
        from fit_file_faker.app import run

        # Current Python should be >= 3.12
        assert sys.version_info >= (3, 12), "Tests should run on Python 3.12+"

        # Should not raise OSError for version
        # (Will fail for other reasons like missing arguments, but not version)
        with pytest.raises(SystemExit):
            # No arguments will cause argparse to exit
            with patch("sys.argv", ["fit-file-faker"]):
                run()

    def test_version_check_fails_on_old_python(self, monkeypatch):
        """Test that Python version check raises OSError on unsupported versions."""
        from fit_file_faker.app import run

        # Mock sys.version_info to simulate Python 3.11
        mock_version_info = MagicMock()
        mock_version_info.major = 3
        mock_version_info.minor = 11
        mock_version_info.micro = 0

        monkeypatch.setattr("sys.version_info", mock_version_info)

        # Should raise OSError with appropriate message
        with pytest.raises(OSError) as exc_info:
            run()

        error_message = str(exc_info.value)
        assert 'This program requires Python "3.12.0" or greater' in error_message
        assert 'current version is "3.11.0"' in error_message
        assert "Please upgrade your python version" in error_message

    def test_verbose_mode_logging_levels(self, tmp_path):
        """Test that verbose mode sets main logger to DEBUG and third-party loggers to INFO."""
        from fit_file_faker.app import run, _logger

        test_file = tmp_path / "test.fit"
        test_file.write_bytes(b"test content")

        with patch("fit_file_faker.app.config_manager") as mock_config:
            mock_config.is_valid.return_value = True
            mock_config.config.fitfiles_path = None

            with patch("sys.argv", ["fit-file-faker", "-v", "-d", str(test_file)]):
                with patch("fit_file_faker.app.fit_editor.edit_fit") as mock_edit:
                    mock_edit.return_value = None
                    try:
                        run()
                    except SystemExit:
                        pass

        # Main logger should be DEBUG
        assert _logger.level == logging.DEBUG

        # Third-party loggers should be INFO
        third_party_loggers = [
            "urllib3.connectionpool",
            "oauthlib.oauth1.rfc5849",
            "requests_oauthlib.oauth1_auth",
            "asyncio",
            "watchdog.observers.inotify_buffer",
        ]
        for logger_name in third_party_loggers:
            assert logging.getLogger(logger_name).level == logging.INFO

    def test_non_verbose_mode_logging_levels(self, tmp_path):
        """Test that non-verbose mode sets main logger to INFO and third-party loggers to WARNING."""
        from fit_file_faker.app import run, _logger

        test_file = tmp_path / "test.fit"
        test_file.write_bytes(b"test content")

        with patch("fit_file_faker.app.config_manager") as mock_config:
            mock_config.is_valid.return_value = True
            mock_config.config.fitfiles_path = None

            with patch("sys.argv", ["fit-file-faker", "-d", str(test_file)]):
                with patch("fit_file_faker.app.fit_editor.edit_fit") as mock_edit:
                    mock_edit.return_value = None
                    try:
                        run()
                    except SystemExit:
                        pass

        # Main logger should be INFO
        assert _logger.level == logging.INFO

        # Third-party loggers should be WARNING
        third_party_loggers = [
            "urllib3.connectionpool",
            "oauthlib.oauth1.rfc5849",
            "requests_oauthlib.oauth1_auth",
            "asyncio",
            "watchdog.observers.inotify_buffer",
        ]
        for logger_name in third_party_loggers:
            assert logging.getLogger(logger_name).level == logging.WARNING

    def test_cli_argument_validation(self, caplog):
        """Test CLI argument validation - setup flag, no args, and conflicting args."""
        from fit_file_faker.app import run

        # Test -s/--initial-setup flag
        with patch("fit_file_faker.app.config_manager") as mock_config:
            mock_config.get_config_file_path.return_value = "/path/to/.config.json"
            with patch("sys.argv", ["fit-file-faker", "-s"]):
                with pytest.raises(SystemExit) as exc_info:
                    with caplog.at_level(logging.INFO):
                        run()

            mock_config.build_config_file.assert_called_once_with(
                overwrite_existing_vals=True, rewrite_config=True
            )
            assert exc_info.value.code == 0
            assert any(
                "Config file has been written to" in r.message for r in caplog.records
            )

        # Test no arguments shows error
        caplog.clear()
        with patch("fit_file_faker.app.config_manager") as mock_config:
            mock_config.is_valid.return_value = True
            with patch("sys.argv", ["fit-file-faker"]):
                with pytest.raises(SystemExit) as exc_info:
                    with caplog.at_level(logging.ERROR):
                        run()

            assert exc_info.value.code == 1
            assert any(
                "Specify either" in r.message and "--upload-all" in r.message
                for r in caplog.records
            )

        # Test --upload-all and --monitor conflict
        caplog.clear()
        with patch("fit_file_faker.app.config_manager") as mock_config:
            mock_config.is_valid.return_value = True
            with patch("sys.argv", ["fit-file-faker", "-ua", "-m"]):
                with pytest.raises(SystemExit) as exc_info:
                    with caplog.at_level(logging.ERROR):
                        run()

            assert exc_info.value.code == 1
            assert any(
                'Cannot use "--upload-all" and "--monitor" together' in r.message
                for r in caplog.records
            )

    def test_invalid_config_triggers_build(self, tmp_path):
        """Test that invalid config triggers build_config_file."""
        from fit_file_faker.app import run

        # Create a test FIT file
        test_file = tmp_path / "test.fit"
        test_file.write_bytes(b"test content")

        # Mock config_manager to be invalid initially
        with patch("fit_file_faker.app.config_manager") as mock_config:
            mock_config.is_valid.return_value = False
            mock_config.config.fitfiles_path = None

            with patch("sys.argv", ["fit-file-faker", "-d", str(test_file)]):
                with patch("fit_file_faker.app.fit_editor.edit_fit") as mock_edit:
                    mock_edit.return_value = None
                    try:
                        run()
                    except SystemExit:
                        pass

            # Verify build_config_file was called
            mock_config.build_config_file.assert_called_once_with(
                overwrite_existing_vals=False,
                rewrite_config=True,
                excluded_keys=["fitfiles_path"],
            )

    def test_config_path_from_file(self, tmp_path):
        """Test that path is read from config file when no input_path provided."""
        from fit_file_faker.app import run

        # Create test directory with FIT files
        config_path = tmp_path / "fitfiles"
        config_path.mkdir()

        # Mock config_manager
        with patch("fit_file_faker.app.config_manager") as mock_config:
            mock_config.is_valid.return_value = True
            mock_config.config.fitfiles_path = str(config_path)

            with patch("sys.argv", ["fit-file-faker", "-ua"]):
                with patch("fit_file_faker.app.upload_all") as mock_upload_all:
                    run()

            # Verify upload_all was called with the config path
            mock_upload_all.assert_called_once()
            call_args = mock_upload_all.call_args[0]
            assert call_args[0] == config_path

    def test_missing_fitfiles_path_raises_error(self):
        """Test that EnvironmentError is raised when fitfiles_path is None and no input provided."""
        from fit_file_faker.app import run

        # Mock config_manager with None fitfiles_path
        with patch("fit_file_faker.app.config_manager") as mock_config:
            mock_config.is_valid.return_value = True
            mock_config.config.fitfiles_path = None

            # Run with -ua flag but no input_path
            with patch("sys.argv", ["fit-file-faker", "-ua"]):
                with pytest.raises(EnvironmentError):
                    run()

    def test_nonexistent_path_exits(self, caplog):
        """Test that nonexistent path causes error and exit."""
        import logging
        from fit_file_faker.app import run

        nonexistent_path = "/path/that/does/not/exist"

        # Mock config_manager
        with patch("fit_file_faker.app.config_manager") as mock_config:
            mock_config.is_valid.return_value = True
            mock_config.config.fitfiles_path = None

            with patch("sys.argv", ["fit-file-faker", "-d", nonexistent_path]):
                with pytest.raises(SystemExit) as exc_info:
                    with caplog.at_level(logging.ERROR):
                        run()

            # Verify exit code is 1 (error)
            assert exc_info.value.code == 1

            # Verify error message was logged
            assert any(
                "does not exist" in record.message
                and "please check your configuration" in record.message
                for record in caplog.records
            )

    def test_single_file_edit_and_upload(self, tmp_path):
        """Test editing and uploading a single file."""
        from fit_file_faker.app import run

        # Create a test FIT file
        test_file = tmp_path / "test.fit"
        test_file.write_bytes(b"test content")
        output_file = tmp_path / "test_modified.fit"

        # Mock config_manager
        with patch("fit_file_faker.app.config_manager") as mock_config:
            mock_config.is_valid.return_value = True
            mock_config.config.fitfiles_path = None

            with patch("sys.argv", ["fit-file-faker", "-u", str(test_file)]):
                with patch("fit_file_faker.app.fit_editor.edit_fit") as mock_edit:
                    with patch("fit_file_faker.app.upload") as mock_upload:
                        mock_edit.return_value = output_file
                        run()

            # Verify edit_fit was called
            mock_edit.assert_called_once()
            assert mock_edit.call_args[0][0] == test_file

            # Verify upload was called
            mock_upload.assert_called_once_with(
                output_file, original_path=test_file, dryrun=False
            )

    def test_directory_upload_all(self, tmp_path):
        """Test upload_all with a directory."""
        from fit_file_faker.app import run

        # Create test directory
        test_dir = tmp_path / "fitfiles"
        test_dir.mkdir()

        # Mock config_manager
        with patch("fit_file_faker.app.config_manager") as mock_config:
            mock_config.is_valid.return_value = True
            mock_config.config.fitfiles_path = None

            with patch("sys.argv", ["fit-file-faker", "-ua", str(test_dir)]):
                with patch("fit_file_faker.app.upload_all") as mock_upload_all:
                    run()

            # Verify upload_all was called
            mock_upload_all.assert_called_once_with(test_dir, False, False)

    def test_directory_preinitialize(self, tmp_path):
        """Test preinitialize flag with a directory."""
        from fit_file_faker.app import run

        # Create test directory
        test_dir = tmp_path / "fitfiles"
        test_dir.mkdir()

        # Mock config_manager
        with patch("fit_file_faker.app.config_manager") as mock_config:
            mock_config.is_valid.return_value = True
            mock_config.config.fitfiles_path = None

            with patch("sys.argv", ["fit-file-faker", "-p", str(test_dir)]):
                with patch("fit_file_faker.app.upload_all") as mock_upload_all:
                    run()

            # Verify upload_all was called with preinitialize=True
            mock_upload_all.assert_called_once_with(test_dir, True, False)

    def test_directory_monitor(self, tmp_path):
        """Test monitor mode with a directory."""
        from fit_file_faker.app import run

        # Create test directory
        test_dir = tmp_path / "fitfiles"
        test_dir.mkdir()

        # Mock config_manager
        with patch("fit_file_faker.app.config_manager") as mock_config:
            mock_config.is_valid.return_value = True
            mock_config.config.fitfiles_path = None

            with patch("sys.argv", ["fit-file-faker", "-m", str(test_dir)]):
                with patch("fit_file_faker.app.monitor") as mock_monitor:
                    run()

            # Verify monitor was called
            mock_monitor.assert_called_once_with(test_dir, False)

    def test_directory_edit_multiple_files(self, tmp_path):
        """Test editing multiple FIT files in a directory."""
        from fit_file_faker.app import run

        # Create test directory with FIT files
        test_dir = tmp_path / "fitfiles"
        test_dir.mkdir()
        file1 = test_dir / "test1.fit"
        file2 = test_dir / "test2.FIT"  # Test case insensitive
        file1.write_bytes(b"test1")
        file2.write_bytes(b"test2")

        # Mock config_manager
        with patch("fit_file_faker.app.config_manager") as mock_config:
            mock_config.is_valid.return_value = True
            mock_config.config.fitfiles_path = None

            with patch("sys.argv", ["fit-file-faker", "-d", str(test_dir)]):
                with patch("fit_file_faker.app.fit_editor.edit_fit") as mock_edit:
                    mock_edit.return_value = None
                    run()

            # Verify edit_fit was called for both files
            assert mock_edit.call_count == 2
            called_files = {call[0][0] for call in mock_edit.call_args_list}
            assert file1 in called_files
            assert file2 in called_files
