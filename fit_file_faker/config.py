"""
Configuration management for Fit File Faker.

Handles configuration file creation, validation, and management.
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


@dataclass
class Config:
    """Configuration data class for Fit File Faker."""
    garmin_username: str | None = None
    garmin_password: str | None = None
    fitfiles_path: Path | None = None


class ConfigManager:
    """Manages configuration file operations and validation."""
    
    def __init__(self):
        self.config_file = dirs.user_config_path / ".config.json"
        self.config_keys = ["garmin_username", "garmin_password", "fitfiles_path"]
        self.config = self._load_config()
    
    def _load_config(self) -> Config:
        """Load configuration from file or create new Config if file doesn't exist."""
        self.config_file.touch(exist_ok=True)
        
        with self.config_file.open("r") as f:
            if self.config_file.stat().st_size == 0:
                return Config()
            else:
                return Config(**json.load(f))
    
    def save_config(self) -> None:
        """Save current configuration to file."""
        with self.config_file.open("w") as f:
            json.dump(asdict(self.config), f, indent=2)
    
    def is_valid(self, excluded_keys: list[str] | None = None) -> bool:
        """Check if configuration is valid (all required keys have values)."""
        if excluded_keys is None:
            excluded_keys = []
            
        missing_vals = []
        for k in self.config_keys:
            if (
                not hasattr(self.config, k) or getattr(self.config, k) is None
            ) and k not in excluded_keys:
                missing_vals.append(k)
        
        if missing_vals:
            _logger.error(f"The following configuration values are missing: {missing_vals}")
            return False
        return True
    
    def build_config_file(
        self,
        overwrite_existing_vals: bool = False,
        rewrite_config: bool = True,
        excluded_keys: list[str] | None = None,
    ) -> None:
        """Interactively build configuration file."""
        if excluded_keys is None:
            excluded_keys = []
            
        for k in self.config_keys:
            if (
                getattr(self.config, k) is None or overwrite_existing_vals
            ) and k not in excluded_keys:
                valid_input = False
                while not valid_input:
                    try:
                        if not hasattr(self.config, k) or getattr(self.config, k) is None:
                            _logger.warning(f'Required value "{k}" not found in config')
                        msg = f'Enter value to use for "{k}"'

                        if hasattr(self.config, k) and getattr(self.config, k):
                            msg += f'\nor press enter to use existing value of "{getattr(self.config, k)}"'
                            if k == "garmin_password":
                                msg = msg.replace(getattr(self.config, k), "<**hidden**>")

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
        
        config_content = json.dumps(asdict(self.config), indent=2)
        if (
            hasattr(self.config, "garmin_password")
            and getattr(self.config, "garmin_password") is not None
        ):
            config_content = config_content.replace(
                cast(str, self.config.garmin_password), "<**hidden**>"
            )
        _logger.info(f"Config file is now:\n{config_content}")
    
    def get_config_file_path(self) -> Path:
        """Get the path to the configuration file."""
        return self.config_file


def get_fitfiles_path(existing_path: Path | None) -> Path:
    """
    Will attempt to auto-find the FITFiles folder inside a TPVirtual data directory.

    On OSX/Windows, TPVirtual data directory will be auto-detected. This folder can
    be overridden using the ``TPV_DATA_PATH`` environment variable.
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
    """Get the TrainingPeaks Virtual folder path."""
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