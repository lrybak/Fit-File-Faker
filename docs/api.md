# API Reference

This page documents the public API for Fit File Faker.

## Main Application interface (`app.py`)

::: fit_file_faker.app
      options:
        show_root_heading: false
        show_source: true
        show_root_toc_entry: false

## FIT Editor (`fit_editor.py`)

::: fit_file_faker.fit_editor.FitEditor
    options:
      members:
        - edit_fit
        - rewrite_file_id_message
        - get_date_from_fit
        - strip_unknown_fields
        - _should_modify_manufacturer
        - _should_modify_device_info
      show_root_heading: true
      show_source: true

## Configuration (`config.py`)

::: fit_file_faker.config
    options:
      show_root_heading: false
      show_source: true
      show_root_toc_entry: false
      filters:
       - "!^default"

## Utilities (`utils.py`)

::: fit_file_faker.utils
    options:
      show_root_heading: true
      filters:
       - ".*"
