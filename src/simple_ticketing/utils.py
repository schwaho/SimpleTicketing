"""
This module provides utility functions for working with configuration files.
It includes functionality to load configuration settings from a YAML file.
"""

import os
import re
import logging
from typing import Any, List, Dict, Union, Optional, cast
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import dns.resolver
import yaml
from dateutil import parser
from flask import current_app

logger = logging.getLogger(__name__)


def load_config(config_file: str, key: str) -> Any:
    """
    Loads configuration settings from a YAML file.

    Args:
        config_file (str): Config file name e.g. app.yaml
        key (str): The configuration section or key to be loaded.

    Returns:
        dict: A dictionary containing the configuration settings.

    Raises:
        FileNotFoundError: If the YAML configuration file is not found.
        KeyError: If the specified key is not present in the configuration file.
    """

    config_path = os.path.join("instance", config_file)
    if not os.path.isfile(config_path):
        raise FileNotFoundError(f"Configuration file '{config_path}' not found.")

    try:
        with open(config_path, "r", encoding="utf-8") as file:
            yaml_data = yaml.safe_load(file) or {}

            if not isinstance(yaml_data, dict):
                raise ValueError(
                    f"Invalid configuration format in '{config_path}'. Expected a dictionary."
                )
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML syntax in '{config_path}'.") from e

    config = yaml_data.get(key, {})
    if not config:
        raise KeyError(f"'{key}' is not found in '{config_path}'.")

    return config


def validate_config(config: Dict[str, Any], keys: Optional[List[str]]) -> None:
    """
    Validate Keys of a given config.

    Args:
        config (dict): The configuration dictionary to validate.
        keys (List[str]): List of keys to be checked for existence in the config.
                          If None, no keys will be checked.

    Raises:
        KeyError: If a required key is not present in the configuration file.
        TypeError: If the config parameter is not type Dict.
    """
    if not isinstance(config, dict):
        raise TypeError("Expected 'config' to be a dictionary.")

    if keys is not None:
        missing_keys = [key for key in keys if key not in config]
        if missing_keys:
            error_msg = f"Missing required keys in config: {', '.join(missing_keys)}"
            logger.error(error_msg)
            raise KeyError(error_msg)


def load_mail_config() -> Dict[str, Any]:
    """
    Load and validate the email configuration settings from a YAML file.

    Returns:
        Dict[str, Any]: A dictionary containing the validated email configuration.

    Raises:
        FileNotFoundError: If the configuration file is missing.
        KeyError: If required configuration keys are missing.
        ValueError: If the configuration file is empty or has an invalid format.
    """
    config_path = os.path.join("instance", "email.yaml")
    if not os.path.isfile(config_path):
        raise FileNotFoundError(f"Configuration file '{config_path}' not found.")

    try:
        with open(config_path, "r", encoding="utf-8") as file:
            email_config = yaml.safe_load(file)

            if not isinstance(email_config, dict):
                raise ValueError(
                    f"Invalid configuration format in '{config_path}'. Expected a dictionary."
                )

    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML syntax in '{config_path}'.") from e

    if "email" not in email_config:
        raise KeyError("Missing 'email' section in configuration.")

    required_keys = [
        "mail_server",
        "mail_port",
        "mail_use_ssl",
        "mail_username",
        "mail_password",
        "mail_sender_name",
        "mail_sender_email",
    ]

    validate_config(email_config["email"], required_keys)

    email_config["email"]["mail_use_tls"] = not email_config["email"]["mail_use_ssl"]

    return cast(Dict[str, Any], email_config["email"])


def get_file_name(path: str) -> str:
    """
    Get a file name from a path string.

    Args:
        path (str): Path to a file

        Returns:
            str: filename

    Raises:
        ValueError: If no valid file name is found.
    """

    file_name = os.path.basename(path)
    if not file_name:
        raise ValueError("The provided path does not contain a valid file name.")
    return file_name


def check_path(path: str) -> Union[str, None]:
    """
    Checks if a given path exist

    Args:
        path (str): Path that have to be checked

    Returns:
        str | None: Path if path exist else retuns None
    """

    if os.path.exists(path):
        return path
    return None


def validate_email(email: str) -> bool:
    """
    Checks whether an email address has a valid format and whether the domain has MX records.

    Args:
        email (str): The email address to be checked.

    Returns:
        bool: True if the email address is valid and the domain has MX records, otherwise False.
    """
    # Regular expression for a valid e-mail address
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"

    if not re.match(pattern, email):
        return False  # Invalid format

    domain = email.split("@")[-1]

    try:
        # Check if MX records exist for the domain
        answers = dns.resolver.resolve(domain, "MX")
        return len(answers) > 0  # True if at least one MX record was found
    except dns.resolver.NoAnswer:
        logger.debug("No MX record exist for '%s'", domain)
        return False
    except dns.resolver.NXDOMAIN:
        logger.debug("Domain '%s' does not exist", domain)
        return False
    except dns.exception.DNSException:
        logger.debug("General DNS error")
        return False


def get_qr_code_path(ticket_code: str) -> str:
    """
    Generates the file path for the QR code of a given ticket.

    Args:
        ticket_code (str): The unique code associated with the ticket.

    Returns:
        str: The file path where the QR code image is stored.

    Raises:
        TypeError: If `ticket_code` is not a string.
        ValueError: If `ticket_code` is empty or contains only whitespace.
    """
    if not isinstance(ticket_code, str):
        raise TypeError("ticket_code must be String.")
    if ticket_code.strip() == "":
        raise ValueError("ticket_code must not be empty.")
    path = os.path.join(current_app.config["QR_PATH"], f"{ticket_code}.png")
    return path


def check_qr_code_path(ticket_code: str) -> Union[str, None]:
    """
    Checks if the QR code file for a given ticket exists.

    Args:
        ticket_code (str): The unique code associated with the ticket.

    Returns:
        str: The file path of the QR code if it exists.
        None: Otherwise.
    """
    path = get_qr_code_path(ticket_code)
    return check_path(path)


def get_ticket_img_path(ticket_code: str) -> str:
    """
    Generates the file path for the ticket image of a given ticket.

    Args:
        ticket_code (str): The unique code associated with the ticket.

    Returns:
        str: The file path where the ticket image is stored.

    Raises:
        TypeError: If `ticket_code` is not a string.
        ValueError: If `ticket_code` is empty or contains only whitespace.
    """
    if not isinstance(ticket_code, str):
        raise TypeError("ticket_code must be String.")
    if ticket_code.strip() == "":
        raise ValueError("ticket_code must not be empty.")
    path = os.path.join(current_app.config["TICKET_IMAGE_PATH"], f"{ticket_code}.png")
    return path


def check_ticket_img_path(ticket_code: str) -> Union[str, None]:
    """
    Checks if the ticket image file for a given ticket exists.

    Args:
        ticket_code (str): The unique code associated with the ticket.

    Returns:
        str: The file path of the ticket image if it exists.
        None: Otherwise.
    """
    path = get_ticket_img_path(ticket_code)
    return check_path(path)


def get_ticket_pdf_path(ticket_code: str) -> str:
    """
    Generates the file path for the PDF ticket of a given ticket code.

    Args:
        ticket_code (str): The unique code associated with the ticket.

    Returns:
        str: The file path where the ticket's PDF file is stored.

    Raises:
        TypeError: If `ticket_code` is not a string.
        ValueError: If `ticket_code` is empty or contains only whitespace.
    """
    if not isinstance(ticket_code, str):
        raise TypeError("ticket_code must be String.")
    if ticket_code.strip() == "":
        raise ValueError("ticket_code must not be empty.")
    path = os.path.join(current_app.config["TICKET_PDF_PATH"], f"{ticket_code}.pdf")
    return path


def check_ticket_pdf_path(ticket_code: str) -> Union[str, None]:
    """
    Checks if the ticket PDF file for a given ticket exists.

    Args:
        ticket_code (str): The unique code associated with the ticket.

    Returns:
        str: The file path of the ticket PDF if it exists.
        None: Otherwise.
    """
    path = get_ticket_pdf_path(ticket_code)
    return check_path(path)


def delete_file(path: str) -> None:
    """
    Deletes a file at the given path.

    Args:
        path (str): Path to the file that should be deleted.

    Raises:
        FileNotFoundError: If the file does not exist.
        RuntimeError: If an error occurs during deletion,
            e.g., due to permission issues or filesystem errors.
    """

    try:
        os.remove(path)
        logger.info("File deleted successfully: %s", path)

    except FileNotFoundError as e:
        logger.warning("File does not exist and cannot be deleted: %s", path)
        raise e

    except OSError as e:
        logger.critical("Failed to delete File: %s", path)
        raise RuntimeError(f"Error deleting File: {e}") from e


def is_none_or_empty(val: Any) -> bool:
    """
    Checks if the argument is None or if the argument is type string empty.

    Args:
        val: Value to be checked.

        Returns:
            bool: True if val is None or empty string, else False.
    """
    return val is None or (isinstance(val, str) and val.strip() == "")


def utc_to_local(
    utc_time_str: str,
    local_zone: str = "Europe/Berlin",
    output_format: str = "%Y-%m-%d %H:%M:%S",
) -> str:
    """
    Converts a UTC timestamp (ISO8601-compatible) to local time.

    Supports all common ISO8601 time formats and automatically takes into account
    summer/winter time based on the specified time zone.

    Args:
        utc_time_str (str): UTC time as an ISO8601-compatible string.
        local_zone (str): Target time zone according to the IANA database (e.g., 'Europe/Berlin').
        output_format (str): Format string for the output according to strftime syntax
                             (e.g. '%d.%m.%Y %H:%M').

    Returns:
        str: Local time as a formatted string according to `output_format`.

    Raises:
        ValueError:
            - If the time string is invalid or cannot be parsed.
            - If the time zone cannot be found.
            - If the conversion to UTC or local time fails.
            - If the format string is invalid or strftime fails.
    """
    utc_zone = ZoneInfo("UTC")
    if is_none_or_empty(output_format):
        raise ValueError("Argument 'output_format' must not be None or an empty string.")

    try:
        utc_dt = parser.isoparse(utc_time_str)
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid time string '{utc_time_str}'. Details: {e}") from e

    try:
        if utc_dt.tzinfo is None:
            utc_dt = utc_dt.replace(tzinfo=ZoneInfo("UTC"))
        elif utc_dt.utcoffset() != utc_zone.utcoffset(utc_dt):
            utc_dt = utc_dt.astimezone(ZoneInfo("UTC"))
    except (ZoneInfoNotFoundError, ValueError, TypeError) as e:
        raise ValueError(f"Error setting the UTC time zone: {e}") from e

    try:
        local_dt = utc_dt.astimezone(ZoneInfo(local_zone))
    except ZoneInfoNotFoundError as e:
        raise ValueError(
            f"Invalid time zone: '{local_zone}'. Please use a valid IANA time zone."
        ) from e
    except (ValueError, TypeError) as e:
        raise ValueError(f"Error converting to local time zone: {e}") from e

    try:
        return local_dt.strftime(output_format)
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid format string: '{output_format}'. Details: {e}") from e


def remove_none_from_dict(data: Dict[Any, Any]) -> Dict[Any, Any]:
    """
    Removes all key-value pairs from the input dictionary where the value is None.

    Args:
        data (Dict[Any, Any]): The dictionary from which None values should be removed.

    Returns:
        Dict[Any, Any]: A new dictionary with all None values removed.
    """
    return {key: value for key, value in data.items() if value is not None}
