"""
Unit tests for generate_apt_auth.py script.

Tests cover both happy and unhappy paths for APT authentication file generation.
"""

import json
import sys
from pathlib import Path
from unittest.mock import Mock, mock_open, patch, call

import pytest
from botocore.exceptions import ClientError

# Add the script directory to the path so we can import it
SCRIPT_DIR = Path(__file__).parent.parent / "files" / "apt_auth"
sys.path.insert(0, str(SCRIPT_DIR))

from generate_apt_auth import generate_apt_auth


# Happy Path Tests


def test_generate_auth_single_repository(tmp_path: Path) -> None:
    """
    Test successful auth file generation for a single repository.

    :param tmp_path: Pytest temporary directory fixture
    :return: None
    """
    # Setup
    auth_inputs_file = tmp_path / "auth_inputs.json"

    # Create auth inputs
    auth_inputs = [
        {
            "machine": "repo.example.com",
            "authFrom": "arn:aws:secretsmanager:us-west-2:123456789012:secret:repo-creds",
        }
    ]
    auth_inputs_file.write_text(json.dumps(auth_inputs))

    # Mock AWS Secrets Manager response
    mock_secret = {"username": "mypassword123"}
    mock_client = Mock()
    mock_client.get_secret_value.return_value = {
        "SecretString": json.dumps(mock_secret)
    }

    # Mock only the write to /etc/apt/auth.conf.d/50user
    m = mock_open()

    with patch("generate_apt_auth.boto3.client", return_value=mock_client), patch(
        "generate_apt_auth.open",
        side_effect=lambda path, *args, **kwargs: (
            m(path, *args, **kwargs)
            if "/etc/apt" in str(path)
            else open(path, *args, **kwargs)
        ),
    ) as mock_file_open, patch("generate_apt_auth.os.chmod") as mock_chmod:

        # Execute
        generate_apt_auth(str(auth_inputs_file))

        # Verify boto3 was called correctly
        mock_client.get_secret_value.assert_called_once_with(
            SecretId="arn:aws:secretsmanager:us-west-2:123456789012:secret:repo-creds"
        )

        # Verify chmod was called with 0o600
        mock_chmod.assert_called_once_with("/etc/apt/auth.conf.d/50user", 0o600)

        # Verify file content was written
        handle = m()
        handle.write.assert_called_once_with(
            "machine repo.example.com login username password mypassword123\n"
        )


def test_generate_auth_multiple_repositories(tmp_path: Path) -> None:
    """
    Test successful auth file generation for multiple repositories.

    :param tmp_path: Pytest temporary directory fixture
    :return: None
    """
    # Setup
    auth_inputs_file = tmp_path / "auth_inputs.json"

    # Create auth inputs for multiple repositories
    auth_inputs = [
        {
            "machine": "repo1.example.com",
            "authFrom": "arn:aws:secretsmanager:us-west-2:123456789012:secret:repo1",
        },
        {
            "machine": "repo2.example.com",
            "authFrom": "arn:aws:secretsmanager:us-west-2:123456789012:secret:repo2",
        },
    ]
    auth_inputs_file.write_text(json.dumps(auth_inputs))

    # Mock AWS Secrets Manager responses
    mock_client = Mock()
    mock_client.get_secret_value.side_effect = [
        {"SecretString": json.dumps({"user1": "pass1"})},
        {"SecretString": json.dumps({"user2": "pass2"})},
    ]

    m = mock_open()

    with patch("generate_apt_auth.boto3.client", return_value=mock_client), patch(
        "generate_apt_auth.open",
        side_effect=lambda path, *args, **kwargs: (
            m(path, *args, **kwargs)
            if "/etc/apt" in str(path)
            else open(path, *args, **kwargs)
        ),
    ), patch("generate_apt_auth.os.chmod"):

        # Execute
        generate_apt_auth(str(auth_inputs_file))

        # Verify both secrets were fetched
        assert mock_client.get_secret_value.call_count == 2

        # Verify both entries were written
        handle = m()
        assert handle.write.call_count == 2
        handle.write.assert_any_call(
            "machine repo1.example.com login user1 password pass1\n"
        )
        handle.write.assert_any_call(
            "machine repo2.example.com login user2 password pass2\n"
        )


def test_file_permissions_set_correctly(tmp_path: Path) -> None:
    """
    Test that file permissions are set to 0600 to protect passwords.

    :param tmp_path: Pytest temporary directory fixture
    :return: None
    """
    # Setup
    auth_inputs_file = tmp_path / "auth_inputs.json"
    auth_inputs = [{"machine": "repo.example.com", "authFrom": "arn:aws:secret"}]
    auth_inputs_file.write_text(json.dumps(auth_inputs))

    mock_client = Mock()
    mock_client.get_secret_value.return_value = {
        "SecretString": json.dumps({"user": "pass"})
    }

    m = mock_open()

    with patch("generate_apt_auth.boto3.client", return_value=mock_client), patch(
        "generate_apt_auth.open",
        side_effect=lambda path, *args, **kwargs: (
            m(path, *args, **kwargs)
            if "/etc/apt" in str(path)
            else open(path, *args, **kwargs)
        ),
    ), patch("generate_apt_auth.os.chmod") as mock_chmod:

        # Execute
        generate_apt_auth(str(auth_inputs_file))

        # Verify chmod was called with correct permissions
        mock_chmod.assert_called_once()
        args = mock_chmod.call_args[0]
        assert args[0] == "/etc/apt/auth.conf.d/50user"
        assert args[1] == 0o600  # rw-------


# Unhappy Path Tests


def test_missing_auth_inputs_file() -> None:
    """
    Test handling of missing auth inputs file.

    Should raise FileNotFoundError with clear error message.

    :return: None
    """
    mock_client = Mock()
    m = mock_open()

    with patch("generate_apt_auth.boto3.client", return_value=mock_client), patch(
        "generate_apt_auth.open",
        side_effect=lambda path, *args, **kwargs: (
            m(path, *args, **kwargs)
            if "/etc/apt" in str(path)
            else open(path, *args, **kwargs)
        ),
    ), pytest.raises(FileNotFoundError):
        generate_apt_auth("/nonexistent/path/auth_inputs.json")


def test_invalid_json_in_auth_inputs(tmp_path: Path) -> None:
    """
    Test handling of invalid JSON in auth inputs file.

    Should raise json.JSONDecodeError.

    :param tmp_path: Pytest temporary directory fixture
    :return: None
    """
    # Setup
    auth_inputs_file = tmp_path / "auth_inputs.json"
    auth_inputs_file.write_text("{ invalid json content }")

    mock_client = Mock()
    m = mock_open()

    # Execute & Verify
    with patch("generate_apt_auth.boto3.client", return_value=mock_client), patch(
        "generate_apt_auth.open",
        side_effect=lambda path, *args, **kwargs: (
            m(path, *args, **kwargs)
            if "/etc/apt" in str(path)
            else open(path, *args, **kwargs)
        ),
    ), pytest.raises(json.JSONDecodeError):
        generate_apt_auth(str(auth_inputs_file))


def test_empty_auth_inputs_file(tmp_path: Path) -> None:
    """
    Test handling of empty auth inputs file.

    Should handle gracefully (no repos to configure).

    :param tmp_path: Pytest temporary directory fixture
    :return: None
    """
    # Setup
    auth_inputs_file = tmp_path / "auth_inputs.json"
    auth_inputs_file.write_text("[]")

    mock_client = Mock()
    m = mock_open()

    with patch("generate_apt_auth.boto3.client", return_value=mock_client), patch(
        "generate_apt_auth.open",
        side_effect=lambda path, *args, **kwargs: (
            m(path, *args, **kwargs)
            if "/etc/apt" in str(path)
            else open(path, *args, **kwargs)
        ),
    ), patch("generate_apt_auth.os.chmod"):

        # Execute - should not raise exception
        generate_apt_auth(str(auth_inputs_file))

        # Verify no secrets were fetched
        mock_client.get_secret_value.assert_not_called()


def test_secret_not_found_in_secrets_manager(tmp_path: Path) -> None:
    """
    Test handling of missing secret in AWS Secrets Manager.

    Should raise ClientError with ResourceNotFoundException.

    :param tmp_path: Pytest temporary directory fixture
    :return: None
    """
    # Setup
    auth_inputs_file = tmp_path / "auth_inputs.json"
    auth_inputs = [
        {"machine": "repo.example.com", "authFrom": "arn:aws:secret:nonexistent"}
    ]
    auth_inputs_file.write_text(json.dumps(auth_inputs))

    # Mock AWS Secrets Manager to raise ResourceNotFoundException
    mock_client = Mock()
    error_response = {
        "Error": {"Code": "ResourceNotFoundException", "Message": "Secret not found"}
    }
    mock_client.get_secret_value.side_effect = ClientError(
        error_response, "GetSecretValue"
    )

    m = mock_open()

    with patch("generate_apt_auth.boto3.client", return_value=mock_client), patch(
        "generate_apt_auth.open",
        side_effect=lambda path, *args, **kwargs: (
            m(path, *args, **kwargs)
            if "/etc/apt" in str(path)
            else open(path, *args, **kwargs)
        ),
    ):

        # Execute & Verify
        with pytest.raises(ClientError) as exc_info:
            generate_apt_auth(str(auth_inputs_file))

        assert exc_info.value.response["Error"]["Code"] == "ResourceNotFoundException"


def test_invalid_json_in_secret_value(tmp_path: Path) -> None:
    """
    Test handling of invalid JSON in secret value from Secrets Manager.

    Should raise json.JSONDecodeError.

    :param tmp_path: Pytest temporary directory fixture
    :return: None
    """
    # Setup
    auth_inputs_file = tmp_path / "auth_inputs.json"
    auth_inputs = [{"machine": "repo.example.com", "authFrom": "arn:aws:secret"}]
    auth_inputs_file.write_text(json.dumps(auth_inputs))

    # Mock Secrets Manager to return invalid JSON
    mock_client = Mock()
    mock_client.get_secret_value.return_value = {"SecretString": "{ invalid json }"}

    m = mock_open()

    with patch("generate_apt_auth.boto3.client", return_value=mock_client), patch(
        "generate_apt_auth.open",
        side_effect=lambda path, *args, **kwargs: (
            m(path, *args, **kwargs)
            if "/etc/apt" in str(path)
            else open(path, *args, **kwargs)
        ),
    ):

        # Execute & Verify
        with pytest.raises(json.JSONDecodeError):
            generate_apt_auth(str(auth_inputs_file))


def test_empty_secret_value(tmp_path: Path) -> None:
    """
    Test handling of empty secret value from Secrets Manager.

    Should raise an appropriate error (IndexError or KeyError).

    :param tmp_path: Pytest temporary directory fixture
    :return: None
    """
    # Setup
    auth_inputs_file = tmp_path / "auth_inputs.json"
    auth_inputs = [{"machine": "repo.example.com", "authFrom": "arn:aws:secret"}]
    auth_inputs_file.write_text(json.dumps(auth_inputs))

    # Mock Secrets Manager to return empty object
    mock_client = Mock()
    mock_client.get_secret_value.return_value = {"SecretString": "{}"}

    m = mock_open()

    with patch("generate_apt_auth.boto3.client", return_value=mock_client), patch(
        "generate_apt_auth.open",
        side_effect=lambda path, *args, **kwargs: (
            m(path, *args, **kwargs)
            if "/etc/apt" in str(path)
            else open(path, *args, **kwargs)
        ),
    ):

        # Execute & Verify - empty dict will cause IndexError when accessing list(auth.keys())[0]
        with pytest.raises(IndexError):
            generate_apt_auth(str(auth_inputs_file))


def test_missing_machine_key_in_auth_input(tmp_path: Path) -> None:
    """
    Test handling of missing 'machine' key in auth input.

    Should raise KeyError.

    :param tmp_path: Pytest temporary directory fixture
    :return: None
    """
    # Setup
    auth_inputs_file = tmp_path / "auth_inputs.json"
    auth_inputs = [{"authFrom": "arn:aws:secret"}]  # Missing 'machine'
    auth_inputs_file.write_text(json.dumps(auth_inputs))

    mock_client = Mock()
    m = mock_open()

    # Execute & Verify
    with patch("generate_apt_auth.boto3.client", return_value=mock_client), patch(
        "generate_apt_auth.open",
        side_effect=lambda path, *args, **kwargs: (
            m(path, *args, **kwargs)
            if "/etc/apt" in str(path)
            else open(path, *args, **kwargs)
        ),
    ), pytest.raises(KeyError):
        generate_apt_auth(str(auth_inputs_file))


def test_missing_authfrom_key_in_auth_input(tmp_path: Path) -> None:
    """
    Test handling of missing 'authFrom' key in auth input.

    Should raise KeyError.

    :param tmp_path: Pytest temporary directory fixture
    :return: None
    """
    # Setup
    auth_inputs_file = tmp_path / "auth_inputs.json"
    auth_inputs = [{"machine": "repo.example.com"}]  # Missing 'authFrom'
    auth_inputs_file.write_text(json.dumps(auth_inputs))

    mock_client = Mock()
    m = mock_open()

    # Execute & Verify
    with patch("generate_apt_auth.boto3.client", return_value=mock_client), patch(
        "generate_apt_auth.open",
        side_effect=lambda path, *args, **kwargs: (
            m(path, *args, **kwargs)
            if "/etc/apt" in str(path)
            else open(path, *args, **kwargs)
        ),
    ), pytest.raises(KeyError):
        generate_apt_auth(str(auth_inputs_file))


def test_permission_error_writing_auth_file(tmp_path: Path) -> None:
    """
    Test handling of permission error when writing auth file.

    Should raise PermissionError.

    :param tmp_path: Pytest temporary directory fixture
    :return: None
    """
    # Setup
    auth_inputs_file = tmp_path / "auth_inputs.json"
    auth_inputs = [{"machine": "repo.example.com", "authFrom": "arn:aws:secret"}]
    auth_inputs_file.write_text(json.dumps(auth_inputs))

    mock_client = Mock()

    # Mock file open to raise PermissionError when opening output file
    def open_side_effect(path, *args, **kwargs):
        if "/etc/apt" in str(path) and "w" in args:
            raise PermissionError("Permission denied: /etc/apt/auth.conf.d/50user")
        return open(path, *args, **kwargs)

    with patch("generate_apt_auth.boto3.client", return_value=mock_client), patch(
        "generate_apt_auth.open", side_effect=open_side_effect
    ):

        # Execute & Verify
        with pytest.raises(PermissionError) as exc_info:
            generate_apt_auth(str(auth_inputs_file))

        assert "Permission denied" in str(exc_info.value)


def test_permission_error_setting_chmod(tmp_path: Path) -> None:
    """
    Test handling of permission error when setting file permissions.

    Should raise PermissionError from os.chmod.

    :param tmp_path: Pytest temporary directory fixture
    :return: None
    """
    # Setup
    auth_inputs_file = tmp_path / "auth_inputs.json"
    auth_inputs = [{"machine": "repo.example.com", "authFrom": "arn:aws:secret"}]
    auth_inputs_file.write_text(json.dumps(auth_inputs))

    mock_client = Mock()
    mock_client.get_secret_value.return_value = {
        "SecretString": json.dumps({"user": "pass"})
    }

    m = mock_open()

    with patch("generate_apt_auth.boto3.client", return_value=mock_client), patch(
        "generate_apt_auth.open",
        side_effect=lambda path, *args, **kwargs: (
            m(path, *args, **kwargs)
            if "/etc/apt" in str(path)
            else open(path, *args, **kwargs)
        ),
    ), patch(
        "generate_apt_auth.os.chmod",
        side_effect=PermissionError("Cannot change permissions"),
    ):

        # Execute & Verify
        with pytest.raises(PermissionError) as exc_info:
            generate_apt_auth(str(auth_inputs_file))

        assert "Cannot change permissions" in str(exc_info.value)


def test_aws_access_denied_error(tmp_path: Path) -> None:
    """
    Test handling of AWS AccessDeniedException when fetching secret.

    Should raise ClientError with AccessDeniedException.

    :param tmp_path: Pytest temporary directory fixture
    :return: None
    """
    # Setup
    auth_inputs_file = tmp_path / "auth_inputs.json"
    auth_inputs = [
        {"machine": "repo.example.com", "authFrom": "arn:aws:secret:forbidden"}
    ]
    auth_inputs_file.write_text(json.dumps(auth_inputs))

    # Mock AWS Secrets Manager to raise AccessDeniedException
    mock_client = Mock()
    error_response = {
        "Error": {
            "Code": "AccessDeniedException",
            "Message": "User is not authorized to perform: secretsmanager:GetSecretValue",
        }
    }
    mock_client.get_secret_value.side_effect = ClientError(
        error_response, "GetSecretValue"
    )

    m = mock_open()

    with patch("generate_apt_auth.boto3.client", return_value=mock_client), patch(
        "generate_apt_auth.open",
        side_effect=lambda path, *args, **kwargs: (
            m(path, *args, **kwargs)
            if "/etc/apt" in str(path)
            else open(path, *args, **kwargs)
        ),
    ):

        # Execute & Verify
        with pytest.raises(ClientError) as exc_info:
            generate_apt_auth(str(auth_inputs_file))

        assert exc_info.value.response["Error"]["Code"] == "AccessDeniedException"
