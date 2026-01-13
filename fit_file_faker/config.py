"""Configuration management for Fit File Faker.

This module handles all configuration file operations including creation,
validation, loading, and saving. Configuration is stored in a platform-specific
user configuration directory using platformdirs.

The configuration includes Garmin Connect credentials and the path to the
directory containing FIT files to process. For TrainingPeaks Virtual users,
the FIT files directory is auto-detected on macOS and Windows.




!!! note "Typical usage example:"
    ```python
    from fit_file_faker.config import config_manager

    # Check if config is valid
    if not config_manager.is_valid():
        config_manager.build_config_file()

    # Access configuration values
    username = config_manager.config.garmin_username
    fit_path = config_manager.config.fitfiles_path
    ```
"""

import json
import logging
import os
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import cast

import questionary
from platformdirs import PlatformDirs

_logger = logging.getLogger("garmin")

# Platform-specific directories for config and cache
dirs = PlatformDirs("FitFileFaker", appauthor=False, ensure_exists=True)


class PathEncoder(json.JSONEncoder):
    """JSON encoder that handles `pathlib.Path` objects.

    Extends `json.JSONEncoder` to automatically convert Path objects to strings
    when serializing configuration to JSON format.

    Examples:
        >>> import json
        >>> from pathlib import Path
        >>> data = {"path": Path("/home/user")}
        >>> json.dumps(data, cls=PathEncoder)
        '{"path": "/home/user"}'
    """

    def default(self, obj):
        """Override default encoding for Path objects.

        Args:
            obj: The object to encode.

        Returns:
            String representation of Path objects, or delegates to the
            parent class for other types.
        """
        if isinstance(obj, Path):
            return str(obj)
        return super().default(obj)  # pragma: no cover


@dataclass
class Config:
    """Configuration data class for Fit File Faker.

    Stores all configuration values including Garmin Connect credentials
    and the path to FIT files directory. All fields are optional to allow
    incremental configuration building.

    Attributes:
        garmin_username: Garmin Connect account email address.
        garmin_password: Garmin Connect account password.
        fitfiles_path: Path to directory containing FIT files to process.
            For TrainingPeaks Virtual, this typically points to the user's
            FITFiles directory within their TPVirtual folder.

    Examples:
        >>> from pathlib import Path
        >>> config = Config(
        ...     garmin_username="user@example.com",
        ...     garmin_password="secret",
        ...     fitfiles_path=Path("/home/user/TPVirtual/abc123/FITFiles")
        ... )
    """

    garmin_username: str | None = None
    garmin_password: str | None = None
    fitfiles_path: Path | None = None


class ConfigManager:
    """Manages configuration file operations and validation.

    Handles loading, saving, and validating configuration stored in a
    platform-specific user configuration directory. Provides interactive
    configuration building for missing or invalid values.

    The configuration file is stored as `.config.json` in the user's
    config directory (location varies by platform).

    Attributes:
        config_file: Path to the JSON configuration file.
        config_keys: List of required configuration keys.
        config: Current Config object loaded from file.

    Examples:
        >>> from fit_file_faker.config import config_manager
        >>>
        >>> # Check if config is valid
        >>> if not config_manager.is_valid():
        ...     print(f"Config file: {config_manager.get_config_file_path()}")
        ...     config_manager.build_config_file()
        >>>
        >>> # Access config values
        >>> username = config_manager.config.garmin_username
    """

    def __init__(self):
        """Initialize the configuration manager.

        Creates the config file if it doesn't exist and loads existing
        configuration or creates a new empty Config object.
        """
        self.config_file = dirs.user_config_path / ".config.json"
        self.config_keys = ["garmin_username", "garmin_password", "fitfiles_path"]
        self.config = self._load_config()

    def _load_config(self) -> Config:
        """Load configuration from file or create new Config if file doesn't exist.

        Returns:
            Loaded Config object if file exists and contains valid JSON,
            otherwise a new empty Config object.

        Note:
            Creates an empty config file if one doesn't exist.
        """
        self.config_file.touch(exist_ok=True)

        with self.config_file.open("r") as f:
            if self.config_file.stat().st_size == 0:
                return Config()
            else:
                return Config(**json.load(f))

    def save_config(self) -> None:
        """Save current configuration to file.

        Serializes the current Config object to JSON and writes it to the
        config file with 2-space indentation. Path objects are automatically
        converted to strings via PathEncoder.
        """
        with self.config_file.open("w") as f:
            json.dump(asdict(self.config), f, indent=2, cls=PathEncoder)

    def is_valid(self, excluded_keys: list[str] | None = None) -> bool:
        """Check if configuration is valid (all required keys have values).

        Args:
            excluded_keys: Optional list of keys to exclude from validation.
                Useful when certain config values aren't needed for specific
                operations (e.g., fitfiles_path when path is provided via CLI).

        Returns:
            True if all required (non-excluded) keys have non-None values,
            False otherwise. Logs missing keys as errors.

        Examples:
            >>> # Check all keys
            >>> if not config_manager.is_valid():
            ...     print("Configuration incomplete")
            >>>
            >>> # Exclude fitfiles_path from validation
            >>> if not config_manager.is_valid(excluded_keys=["fitfiles_path"]):
            ...     print("Missing Garmin credentials")
        """
        if excluded_keys is None:
            excluded_keys = []

        missing_vals = []
        for k in self.config_keys:
            if (
                not hasattr(self.config, k) or getattr(self.config, k) is None
            ) and k not in excluded_keys:
                missing_vals.append(k)

        if missing_vals:
            _logger.error(
                f"The following configuration values are missing: {missing_vals}"
            )
            return False
        return True

    def build_config_file(
        self,
        overwrite_existing_vals: bool = False,
        rewrite_config: bool = True,
        excluded_keys: list[str] | None = None,
    ) -> None:
        """Interactively build configuration file.

        Prompts the user for missing or invalid configuration values using
        questionary for an interactive CLI experience. Passwords are masked
        during input, and the FIT files path is auto-detected for TrainingPeaks
        Virtual users when possible.

        Args:
            overwrite_existing_vals: If `True`, prompts for all values even if
                they already exist. If `False`, only prompts for missing values.
                Defaults to `False`.
            rewrite_config: If `True`, saves the configuration to disk after
                building. If `False`, only updates the in-memory config object.
                Defaults to `True`.
            excluded_keys: Optional list of keys to skip during interactive
                building. Useful for partial configuration.

        Raises:
            SystemExit: If user presses Ctrl-C to cancel configuration.

        Examples:
            >>> # Interactive setup for missing values only
            >>> config_manager.build_config_file()
            >>>
            >>> # Rebuild entire configuration
            >>> config_manager.build_config_file(overwrite_existing_vals=True)
            >>>
            >>> # Update only credentials (skip fitfiles_path)
            >>> config_manager.build_config_file(
            ...     excluded_keys=["fitfiles_path"]
            ... )

        Note:
            Passwords are masked in both user input and log output for security.
            The final configuration is logged with passwords hidden.
        """
        if excluded_keys is None:
            excluded_keys = []

        for k in self.config_keys:
            if (
                getattr(self.config, k) is None or overwrite_existing_vals
            ) and k not in excluded_keys:
                valid_input = False
                while not valid_input:
                    try:
                        if (
                            not hasattr(self.config, k)
                            or getattr(self.config, k) is None
                        ):
                            _logger.warning(f'Required value "{k}" not found in config')
                        msg = f'Enter value to use for "{k}"'

                        if hasattr(self.config, k) and getattr(self.config, k):
                            msg += f'\nor press enter to use existing value of "{getattr(self.config, k)}"'
                            if k == "garmin_password":
                                msg = msg.replace(
                                    getattr(self.config, k), "<**hidden**>"
                                )

                        if k != "fitfiles_path":
                            if "password" in k:
                                val = questionary.password(msg).unsafe_ask()
                            else:
                                val = questionary.text(msg).unsafe_ask()
                        else:
                            val = str(
                                get_fitfiles_path(
                                    Path(self.config.fitfiles_path).parent.parent
                                    if self.config.fitfiles_path
                                    else None
                                )
                            )

                        if val:
                            valid_input = True
                            setattr(self.config, k, val)
                        elif hasattr(self.config, k) and getattr(self.config, k):
                            valid_input = True
                            val = getattr(self.config, k)
                        else:
                            _logger.warning(
                                "Entered input was not valid, please try again (or press Ctrl-C to cancel)"
                            )
                    except KeyboardInterrupt:
                        _logger.error("User canceled input; exiting!")
                        sys.exit(1)

        if rewrite_config:
            self.save_config()

        config_content = json.dumps(asdict(self.config), indent=2, cls=PathEncoder)
        if (
            hasattr(self.config, "garmin_password")
            and getattr(self.config, "garmin_password") is not None
        ):
            config_content = config_content.replace(
                cast(str, self.config.garmin_password), "<**hidden**>"
            )
        _logger.info(f"Config file is now:\n{config_content}")

    def get_config_file_path(self) -> Path:
        """Get the path to the configuration file.

        Returns:
            Path to the .config.json file in the platform-specific user
            configuration directory.

        Examples:
            >>> path = config_manager.get_config_file_path()
            >>> print(f"Config file: {path}")
            Config file: /home/user/.config/FitFileFaker/.config.json
        """
        return self.config_file


def get_fitfiles_path(existing_path: Path | None) -> Path:
    """Auto-find the FITFiles folder inside a TrainingPeaks Virtual directory.

    Attempts to automatically locate the user's TrainingPeaks Virtual FITFiles
    directory. On macOS/Windows, the TPVirtual data directory is auto-detected.
    On Linux, the user is prompted to provide the path.

    If multiple user directories exist, the user is prompted to select one.

    Args:
        existing_path: Optional path to use as default. If provided, this path's
            `parent.parent` is used as the TPVirtual base directory.

    Returns:
        Path to the FITFiles directory (e.g., `~/TPVirtual/abc123def/FITFiles`).

    Raises:
        SystemExit: If no TP Virtual user folder is found, the user rejects
            the auto-detected folder, or the user cancels the selection.

    Note:
        The TPVirtual folder location can be overridden using the
        `TPV_DATA_PATH` environment variable. User directories are identified
        by 16-character hexadecimal folder names.

    Examples:
        >>> # Auto-detect FITFiles path
        >>> path = get_fitfiles_path(None)
        >>> print(path)
        /Users/me/TPVirtual/a1b2c3d4e5f6g7h8/FITFiles
    """
    _logger.info("Getting FITFiles folder")

    TPVPath = get_tpv_folder(existing_path)
    res = [f for f in os.listdir(TPVPath) if re.search(r"\A(\w){16}\Z", f)]
    if len(res) == 0:
        _logger.error(
            'Cannot find a TP Virtual User folder in "%s", please check if you have previously logged into TP Virtual',
            TPVPath,
        )
        sys.exit(1)
    elif len(res) == 1:
        title = f'Found TP Virtual User directory at "{Path(TPVPath) / res[0]}", is this correct? '
        option = questionary.select(title, choices=["yes", "no"]).ask()
        if option == "no":
            # Get config manager instance to access config file path
            config_manager = ConfigManager()
            _logger.error(
                'Failed to find correct TP Virtual User folder please manually configure "fitfiles_path" in config file: %s',
                config_manager.get_config_file_path().absolute(),
            )
            sys.exit(1)
        else:
            option = res[0]
    else:
        title = "Found multiple TP Virtual User directories, please select the directory for your user: "
        option = questionary.select(title, choices=res).ask()
    TPV_data_path = Path(TPVPath) / option
    _logger.info(
        f'Found TP Virtual User directory: "{str(TPV_data_path.absolute())}", '
        'setting "fitfiles_path" in config file'
    )
    return TPV_data_path / "FITFiles"


def get_tpv_folder(default_path: Path | None) -> Path:
    """Get the TrainingPeaks Virtual base folder path.

    Auto-detects the TPVirtual directory based on platform, or prompts the
    user to provide it if auto-detection is not available.

    Platform-specific default locations:

    - macOS: `~/TPVirtual`
    - Windows: `~/Documents/TPVirtual`
    - Linux: User is prompted (no auto-detection)

    Args:
        default_path: Optional default path to show in the prompt for Linux users.

    Returns:
        Path to the `TPVirtual` base directory (not the `FITFiles` subdirectory).

    Note:
        The auto-detected path can be overridden by setting the `TPV_DATA_PATH`
        environment variable.

    Examples:
        >>> # macOS
        >>> path = get_tpv_folder(None)
        >>> print(path)
        /Users/me/TPVirtual
        >>>
        >>> # Linux (prompts user)
        >>> path = get_tpv_folder(Path("/home/me/custom/path"))
        Please enter your TrainingPeaks Virtual data folder: /home/me/TPVirtual
    """
    if os.environ.get("TPV_DATA_PATH", None):
        p = str(os.environ.get("TPV_DATA_PATH"))
        _logger.info(f'Using TPV_DATA_PATH value read from the environment: "{p}"')
        return Path(p)
    if sys.platform == "darwin":
        TPVPath = os.path.expanduser("~/TPVirtual")
    elif sys.platform == "win32":
        TPVPath = os.path.expanduser("~/Documents/TPVirtual")
    else:
        _logger.warning(
            "TrainingPeaks Virtual user folder can only be automatically detected on Windows and OSX"
        )
        TPVPath = questionary.path(
            'Please enter your TrainingPeaks Virtual data folder (by default, ends with "TPVirtual"): ',
            default=str(default_path) if default_path else "",
        ).ask()
    return Path(TPVPath)


# Global configuration manager instance
config_manager = ConfigManager()
