"""
Unit tests for the `simple_ticketing.utils` module.
"""

import ntpath
from unittest import mock
from typing import Dict, Any
import yaml
import pytest
from simple_ticketing.utils import (
    check_path,
    get_file_name,
    load_mail_config,
    validate_config,
    load_config,
    validate_email,
    utc_to_local,
)


@pytest.mark.parametrize(
    "test_case",
    [
        # Test case: Successful loading of a valid key
        {
            "yaml_content": yaml.dump({"database": {"host": "localhost", "port": 5432}}),
            "key": "database",
            "should_raise": False,
            "expected_exception": None,
            "expected_result": {"host": "localhost", "port": 5432},
        },
        # Test case: Key missing
        {
            "yaml_content": yaml.dump({"api": {"url": "https://api.example.com"}}),
            "key": "nonexistent",
            "should_raise": True,
            "expected_exception": KeyError,
            "expected_result": None,
        },
        # Test case: File not found
        {
            "yaml_content": None,
            "key": "database",
            "should_raise": True,
            "expected_exception": FileNotFoundError,
            "expected_result": None,
        },
        # Test case: Empty file
        {
            "yaml_content": "",
            "key": "database",
            "should_raise": True,
            "expected_exception": KeyError,
            "expected_result": None,
        },
        # Test case: Invalid YAML syntax
        {
            "yaml_content": "invalid: yaml: :::",
            "key": "database",
            "should_raise": True,
            "expected_exception": ValueError,
            "expected_result": None,
        },
        # Test case: Wrong format (list instead of dict)
        {
            "yaml_content": yaml.dump(["list_item1", "list_item2"]),
            "key": "database",
            "should_raise": True,
            "expected_exception": ValueError,
            "expected_result": None,
        },
    ],
)
def test_load_config(test_case: Dict[str, Any]) -> None:
    """
    Test the `load_config` function with various scenarios using parameterized test cases.

    Args:
        test_case (dict): Dictionary containing all test case parameters.

    Raises:
        AssertionError: If the test conditions (exception or result) are not met.
    """
    yaml_content = test_case["yaml_content"]
    key = test_case["key"]
    should_raise = test_case["should_raise"]
    expected_exception = test_case["expected_exception"]
    expected_result = test_case["expected_result"]

    if yaml_content is not None:
        mock_file = mock.mock_open(read_data=yaml_content)
    else:
        mock_file = mock.Mock()
        mock_file.side_effect = FileNotFoundError

    with (
        mock.patch("builtins.open", mock_file),
        mock.patch("os.path.join", return_value="config/config.yaml"),
        mock.patch("os.path.isfile", return_value=True),
    ):

        if should_raise and expected_exception:
            with pytest.raises(expected_exception):
                load_config("dummy.yaml", key)
        else:
            result = load_config("dummy.yaml", key)
            assert result == expected_result


@pytest.mark.parametrize(
    "test_case",
    [
        # Test case: All required keys available
        {
            "config": {"key1": "value1", "key2": "value2", "key3": "value3"},
            "keys": ["key1", "key2"],
            "should_raise": False,
            "expected_exception": None,
        },
        # Test case: Missing key
        {
            "config": {"key1": "value1", "key2": "value2"},
            "keys": ["key1", "key3"],
            "should_raise": True,
            "expected_exception": KeyError,
        },
        # Test case: Empty configuration, key required
        {
            "config": {},
            "keys": ["key1", "key2"],
            "should_raise": True,
            "expected_exception": KeyError,
        },
        # Test case: No key required
        {
            "config": {"key1": "value1", "key2": "value2"},
            "keys": [],
            "should_raise": False,
            "expected_exception": None,
        },
        # Test case: keys=None (should not raise an error)
        {
            "config": {"key1": "value1", "key2": "value2"},
            "keys": None,
            "should_raise": False,
            "expected_exception": None,
        },
        # Test case: config is not a dictionary
        {
            "config": ["not", "a", "dict"],
            "keys": ["key1"],
            "should_raise": True,
            "expected_exception": TypeError,
        },
    ],
)
def test_validate_config(test_case: Dict[str, Any]) -> None:
    """
    Test validate_config with various scenarios.

    Args:
        test_case (dict): Dictionary containing all test case parameters.
    """
    config = test_case["config"]
    keys = test_case["keys"]
    should_raise = test_case["should_raise"]
    expected_exception = test_case["expected_exception"]

    if should_raise:
        with pytest.raises(expected_exception):
            validate_config(config, keys)
    else:
        validate_config(config, keys)
        assert True


@pytest.mark.parametrize(
    "test_case",
    [
        # Valid configuration
        {
            "yaml_content": yaml.dump(
                {
                    "email": {
                        "mail_server": "smtp.example.com",
                        "mail_port": 587,
                        "mail_use_ssl": False,
                        "mail_username": "user@example.com",
                        "mail_password": "securepassword",
                        "mail_sender_name": "Example",
                        "mail_sender_email": "noreply@example.com",
                    }
                }
            ),
            "should_raise": False,
            "expected_exception": None,
            "expected_result": {
                "mail_server": "smtp.example.com",
                "mail_port": 587,
                "mail_use_ssl": False,
                "mail_username": "user@example.com",
                "mail_password": "securepassword",
                "mail_sender_name": "Example",
                "mail_sender_email": "noreply@example.com",
                "mail_use_tls": True,  # Check if mail_use_tls is properly set
            },
        },
        # File not found
        {
            "yaml_content": None,
            "should_raise": True,
            "expected_exception": FileNotFoundError,
            "expected_result": None,
        },
        # Empty file
        {
            "yaml_content": "",
            "should_raise": True,
            "expected_exception": ValueError,
            "expected_result": None,
        },
        # Invalid YAML format
        {
            "yaml_content": "invalid: yaml: :::",
            "should_raise": True,
            "expected_exception": ValueError,
            "expected_result": None,
        },
        # Wrong format (list instead of dict)
        {
            "yaml_content": yaml.dump(["wrong", "format"]),
            "should_raise": True,
            "expected_exception": ValueError,
            "expected_result": None,
        },
        # Missing "email" key
        {
            "yaml_content": yaml.dump({"not_email": {}}),
            "should_raise": True,
            "expected_exception": KeyError,
            "expected_result": None,
        },
        # Missing required keys
        {
            "yaml_content": yaml.dump({"email": {"mail_server": "smtp.example.com"}}),
            "should_raise": True,
            "expected_exception": KeyError,
            "expected_result": None,
        },
    ],
)
def test_load_mail_config(test_case: Dict[str, Any]) -> None:
    """
    Test `load_mail_config` with various scenarios.
    """
    yaml_content = test_case["yaml_content"]
    should_raise = test_case["should_raise"]
    expected_exception = test_case["expected_exception"]
    expected_result = test_case["expected_result"]

    if yaml_content is not None:
        mock_file = mock.mock_open(read_data=yaml_content)
    else:
        mock_file = mock.Mock()
        mock_file.side_effect = FileNotFoundError

    with (
        mock.patch("builtins.open", mock_file),
        mock.patch("os.path.join", return_value="instance/email.yaml"),
        mock.patch("os.path.isfile", return_value=True),
    ):

        if should_raise:
            with pytest.raises(expected_exception):
                load_mail_config()
        else:
            result = load_mail_config()
            assert result == expected_result


def test_get_file_name() -> None:
    """
    Test that `get_file_name` correctly extracts the file name from a given path.
    """
    # Test cases
    assert get_file_name("/home/user/documents/file.txt") == "file.txt"
    with mock.patch("os.path.basename", side_effect=ntpath.basename):
        assert get_file_name("C:\\Users\\user\\file.txt") == "file.txt"  # Windows-style path
    assert get_file_name("file.txt") == "file.txt"

    # Test for ValueError on invalid paths
    with pytest.raises(ValueError):
        get_file_name("/home/user/documents/")

    with pytest.raises(ValueError):
        get_file_name("")


def test_check_path_exists() -> None:
    """
    Test that check_path returns the path if the given path exists.
    """
    # This test mocks os.path.exists to always return True.
    with mock.patch("os.path.exists", return_value=True):
        assert check_path("/some/existing/path") == "/some/existing/path"

    # This test mocks os.path.exists to always return False.
    with mock.patch("os.path.exists", return_value=False):
        assert check_path("/some/nonexistent/path") is None


@pytest.mark.parametrize(
    "email, expected",
    [
        ("test@gmail.com", True),  # Valid
        ("user@gfx.ms", False),  # Invalid, no MX Record
        ("invalid@xyz.abc", False),  # Invalid Domain
        ("user@local", False),  # Invalid, not a TLD
        ("user@google.com", True),  # Valid
        ("invalid@", False),  # Invalid, missing Domain
        ("@example.com", False),  # Invalid, missing local part
    ],
)
def test_validate_email(email: str, expected: bool) -> None:
    """
    Test that validate_email returns true/false for a given email
    """

    assert validate_email(email) == expected


@pytest.mark.parametrize(
    "utc_input, local_zone, output_format, expected_output",
    [
        # Standard format, Berlin time
        (
            "2025-08-06T07:00:00Z",
            "Europe/Berlin",
            "%Y-%m-%d %H:%M:%S",
            "2025-08-06 09:00:00",
        ),
        # Standard format, New York time
        (
            "2025-08-06T07:00:00Z",
            "America/New_York",
            "%Y-%m-%d %H:%M:%S",
            "2025-08-06 03:00:00",
        ),
        # Input without time zone
        (
            "2025-08-06 07:00:00",
            "Europe/Berlin",
            "%Y-%m-%d %H:%M:%S",
            "2025-08-06 09:00:00",
        ),
        # Input with offset
        (
            "2025-08-06T07:00:00+00:00",
            "Europe/Berlin",
            "%Y-%m-%d %H:%M:%S",
            "2025-08-06 09:00:00",
        ),
        (
            "2025-08-06T09:00:00+02:00",
            "Europe/Berlin",
            "%Y-%m-%d %H:%M:%S",
            "2025-08-06 09:00:00",
        ),
        # Custom output format
        (
            "2025-08-06T07:00:00Z",
            "Europe/Berlin",
            "%d.%m.%Y %H:%M:%S",
            "06.08.2025 09:00:00",
        ),
    ],
)
def test_utc_to_local_valid_cases(
    utc_input: str, local_zone: str, output_format: str, expected_output: str
) -> None:
    """
    Tests the function `utc_to_local` with valid input values.
    """

    assert utc_to_local(utc_input, local_zone, output_format) == expected_output


@pytest.mark.parametrize(
    "utc_input, local_zone, output_format",
    [
        # Invalid time string
        ("not-a-date", "Europe/Berlin", "%Y-%m-%d %H:%M:%S"),
        ("", "Europe/Berlin", "%Y-%m-%d %H:%M:%S"),
        (None, "Europe/Berlin", "%Y-%m-%d %H:%M:%S"),
        # Invalid time zone
        ("2025-08-06T07:00:00Z", "Invalid/Zone", "%Y-%m-%d %H:%M:%S"),
        ("2025-08-06T07:00:00Z", "", "%Y-%m-%d %H:%M:%S"),
        ("2025-08-06T07:00:00Z", None, "%Y-%m-%d %H:%M:%S"),
        # Invalid format string
        ("2025-08-06T07:00:00Z", "Europe/Berlin", ""),
        ("2025-08-06T07:00:00Z", "Europe/Berlin", None),
    ],
)
def test_utc_to_local_errors(utc_input: str, local_zone: str, output_format: str) -> None:
    """
    Tests the function `utc_to_local` with valid input values.
    """
    with pytest.raises(ValueError):
        utc_to_local(utc_input, local_zone, output_format)
