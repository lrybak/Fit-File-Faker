"""
FIT file editing functionality for Fit File Faker.

This module handles the core FIT file manipulation logic, converting files
from virtual cycling platforms to appear as Garmin Edge 830 recordings.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from fit_tool.definition_message import DefinitionMessage
from fit_tool.fit_file import FitFile
from fit_tool.fit_file_builder import FitFileBuilder
from fit_tool.profile.messages.device_info_message import DeviceInfoMessage
from fit_tool.profile.messages.file_creator_message import FileCreatorMessage
from fit_tool.profile.messages.file_id_message import FileIdMessage
from fit_tool.profile.profile_type import GarminProduct, Manufacturer

_logger = logging.getLogger("garmin")


class FitFileLogFilter(logging.Filter):
    """Filter to remove specific warning from the fit_tool module"""

    def filter(self, record):
        res = "\n\tactual: " not in record.getMessage()
        return res


class FitEditor:
    """Handles FIT file editing and manipulation."""
    
    def __init__(self):
        # Apply the log filter to suppress noisy fit_tool warnings
        logging.getLogger("fit_tool").addFilter(FitFileLogFilter())
    
    def print_message(self, prefix: str, message: FileIdMessage | DeviceInfoMessage) -> None:
        """Print debug information about FIT file messages."""
        man = (
            Manufacturer(message.manufacturer).name
            if message.manufacturer in Manufacturer
            else "BLANK"
        )
        gar_prod = (
            GarminProduct(message.garmin_product)
            if message.garmin_product in GarminProduct
            else "BLANK"
        )
        _logger.debug(f"{prefix} - {message.to_row()=}\n"
                      f"(Manufacturer: {man}, product: {message.product}, garmin_product: {gar_prod})")
    
    def get_date_from_fit(self, fit_path: Path) -> Optional[datetime]:
        """Extract the creation date from a FIT file."""
        fit_file = FitFile.from_file(str(fit_path))
        res = None
        for i, record in enumerate(fit_file.records):
            message = record.message
            if message.global_id == FileIdMessage.ID:
                if isinstance(message, FileIdMessage):
                    res = datetime.fromtimestamp(message.time_created / 1000.0)  # type: ignore
                    break
        return res
    
    def rewrite_file_id_message(
        self, 
        m: FileIdMessage,
        message_num: int,
    ) -> tuple[DefinitionMessage, FileIdMessage]:
        """Rewrite FileIdMessage to appear as if from Garmin Edge 830."""
        dt = datetime.fromtimestamp(m.time_created / 1000.0)  # type: ignore
        _logger.info(f'Activity timestamp is "{dt.isoformat()}"')
        self.print_message(f"FileIdMessage Record: {message_num}", m)

        new_m = FileIdMessage()
        new_m.time_created = (
            m.time_created if m.time_created 
            else int(datetime.now().timestamp() * 1000)
        )
        if m.type:
            new_m.type = m.type
        if m.serial_number is not None:
            new_m.serial_number = m.serial_number
        if m.product_name:
            # garmin does not appear to define product_name, so don't copy it over
            pass
        
        if self._should_modify_manufacturer(m.manufacturer):
            new_m.manufacturer = Manufacturer.GARMIN.value
            new_m.product = GarminProduct.EDGE_830.value
            _logger.debug("    Modifying values")
            self.print_message(f"    New Record: {message_num}", new_m)

        return (DefinitionMessage.from_data_message(new_m), new_m)
    
    def _should_modify_manufacturer(self, manufacturer: int | None) -> bool:
        """Check if manufacturer should be modified to Garmin."""
        if manufacturer is None:
            return False
        return manufacturer in [
            Manufacturer.DEVELOPMENT.value,
            Manufacturer.ZWIFT.value,
            Manufacturer.WAHOO_FITNESS.value,
            Manufacturer.PEAKSWARE.value,
            Manufacturer.HAMMERHEAD.value
        ]
    
    def _should_modify_device_info(self, manufacturer: int | None) -> bool:
        """Check if device info should be modified to Garmin Edge 830."""
        if manufacturer is None:
            return False
        return manufacturer in [
            Manufacturer.DEVELOPMENT.value,
            0,  # Blank/unknown manufacturer
            Manufacturer.WAHOO_FITNESS.value,
            Manufacturer.ZWIFT.value,
            Manufacturer.PEAKSWARE.value,
            Manufacturer.HAMMERHEAD.value
        ]
    
    def edit_fit(
        self, 
        fit_path: Path, 
        output: Optional[Path] = None, 
        dryrun: bool = False
    ) -> Path | None:
        """
        Edit a FIT file to appear as if it came from a Garmin Edge 830.
        
        Args:
            fit_path: Path to the input FIT file
            output: Optional output path (defaults to {original}_modified.fit)
            dryrun: If True, don't actually write the file
            
        Returns:
            Path to the output file, or None if processing failed
        """
        if dryrun:
            _logger.warning('In "dryrun" mode; will not actually write new file.')
        
        _logger.info(f'Processing "{fit_path}"')
        
        try:
            fit_file = FitFile.from_file(str(fit_path))
        except Exception:
            _logger.error("File does not appear to be a FIT file, skipping...")
            return None
        
        if not output:
            output = fit_path.parent / f"{fit_path.stem}_modified.fit"

        builder = FitFileBuilder(auto_define=True)
        
        # Loop through records, find the ones we need to change, and modify the values
        for i, record in enumerate(fit_file.records):
            message = record.message

            # Change file id to indicate file was saved by Edge 830
            if message.global_id == FileIdMessage.ID:
                if isinstance(message, DefinitionMessage):
                    # If this is the definition message for the FileIdMessage, skip it
                    # since we're going to write a new one
                    continue
                if isinstance(message, FileIdMessage):
                    # Rewrite the FileIdMessage and its definition and add to builder
                    def_message, message = self.rewrite_file_id_message(message, i)
                    builder.add(def_message)
                    builder.add(message)
                    # Also add a customized FileCreatorMessage
                    creator_message = FileCreatorMessage()
                    creator_message.software_version = 975
                    creator_message.hardware_version = 255
                    builder.add(DefinitionMessage.from_data_message(creator_message))
                    builder.add(creator_message)
                    continue
            
            if message.global_id == FileCreatorMessage.ID:
                # Skip any existing file creator message
                continue

            # Change device info messages
            if message.global_id == DeviceInfoMessage.ID:
                if isinstance(message, DeviceInfoMessage):
                    self.print_message(f"DeviceInfoMessage Record: {i}", message)
                    if self._should_modify_device_info(message.manufacturer):
                        _logger.debug("    Modifying values")
                        message.garmin_product = GarminProduct.EDGE_830.value
                        message.product = GarminProduct.EDGE_830.value  # type: ignore
                        message.manufacturer = Manufacturer.GARMIN.value
                        message.product_name = ""
                        self.print_message(f"    New Record: {i}", message)

            builder.add(message)

        modified_file = builder.build()
        
        if not dryrun:
            _logger.info(f'Saving modified data to "{output}"')
            modified_file.to_file(str(output))
        else:
            _logger.info(
                f"Dryrun requested, so not saving data "
                f'(would have written to "{output}")'
            )
        
        return output


# Global FIT editor instance
fit_editor = FitEditor()