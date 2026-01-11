"""
Generate APT authentication configuration from AWS Secrets Manager.

This script fetches credentials from AWS Secrets Manager and generates an APT
auth.conf file for authenticating to private APT repositories during EC2 instance
bootstrap.
"""

import json
import logging
import os
import sys
from typing import Any, Dict

import boto3
from botocore.exceptions import ClientError

# Setup logging
LOG = logging.getLogger(__name__)


def generate_apt_auth(auth_inputs: str) -> None:
    """
    Generate APT authentication configuration from AWS Secrets Manager.

    Reads a JSON file containing repository authentication configurations,
    fetches credentials from AWS Secrets Manager, and writes them to
    /etc/apt/auth.conf.d/50user in APT auth.conf format.

    The function processes each repository configuration:
    1. Reads auth_inputs JSON file
    2. For each repository, fetches credentials from AWS Secrets Manager
    3. Writes credentials to /etc/apt/auth.conf.d/50user
    4. Sets file permissions to 0600 for security

    :param auth_inputs: Absolute path to JSON file containing authentication
                        configuration. Expected format:
                        [{"machine": "repo.example.com",
                          "authFrom": "arn:aws:secretsmanager:..."}]
    :type auth_inputs: str
    :return: None
    :rtype: None
    :raises FileNotFoundError: If auth_inputs file does not exist
    :raises json.JSONDecodeError: If auth_inputs contains invalid JSON or if
                                  secret value from Secrets Manager contains
                                  invalid JSON
    :raises KeyError: If required keys ('machine' or 'authFrom') are missing
                      from auth inputs
    :raises IndexError: If secret value is empty dict (no username/password)
    :raises PermissionError: If cannot write to /etc/apt/auth.conf.d/ or
                            set file permissions
    :raises ClientError: If AWS Secrets Manager operations fail (secret not
                         found, access denied, throttling, network errors, etc.)
    """
    LOG.info("Starting APT authentication configuration generation")
    LOG.debug("Reading auth inputs from: %s", auth_inputs)

    client = boto3.client("secretsmanager")
    auth_file = "/etc/apt/auth.conf.d/50user"

    LOG.debug("Opening output file: %s", auth_file)
    with open(auth_file, "w", encoding="utf-8") as auth_fp:
        with open(auth_inputs, "r", encoding="utf-8") as f:
            auth_configs = json.load(f)
            LOG.info("Processing %d repository configurations", len(auth_configs))

            for idx, pair in enumerate(auth_configs, 1):
                machine = pair["machine"]
                auth_from = pair["authFrom"]

                LOG.debug(
                    "Processing repository %d/%d: %s (secret: %s)",
                    idx,
                    len(auth_configs),
                    machine,
                    auth_from,
                )

                # Fetch secret from AWS Secrets Manager
                secret_response = client.get_secret_value(SecretId=auth_from)
                auth: Dict[str, Any] = json.loads(secret_response["SecretString"])

                # Extract username and password (first key-value pair)
                login = list(auth.keys())[0]
                password = auth[login]

                # Write APT auth.conf entry
                auth_line = (
                    f"machine {machine} login {login} password {password}\n"
                )
                auth_fp.write(auth_line)
                LOG.debug("Written auth entry for machine: %s", machine)

    # Set permissions to 600 (rw-------) to protect passwords
    LOG.debug("Setting file permissions to 0600 on %s", auth_file)
    os.chmod(auth_file, 0o600)

    LOG.info(
        "Successfully generated APT auth configuration with %d repositories",
        len(auth_configs),
    )


if __name__ == "__main__":
    from ihlogging import setup_logging

    setup_logging(level=logging.DEBUG if os.environ.get("DEBUG") else logging.INFO)

    if len(sys.argv) != 2:
        LOG.error("Usage: %s <auth_inputs_json_file>", sys.argv[0])
        sys.exit(1)

    try:
        generate_apt_auth(sys.argv[1])
    except FileNotFoundError as e:
        LOG.error("Auth inputs file not found: %s", e)
        sys.exit(1)
    except json.JSONDecodeError as e:
        LOG.error("Invalid JSON: %s", e)
        sys.exit(1)
    except KeyError as e:
        LOG.error("Missing required key in configuration: %s", e)
        sys.exit(1)
    except IndexError as e:
        LOG.error("Empty or invalid secret value: %s", e)
        sys.exit(1)
    except PermissionError as e:
        LOG.error("Permission denied: %s", e)
        sys.exit(1)
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        error_message = e.response["Error"]["Message"]
        LOG.error("AWS error (%s): %s", error_code, error_message)
        sys.exit(1)
