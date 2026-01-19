import json
from base64 import b64decode
from os import path as osp, remove
from textwrap import dedent
from typing import Any

import pytest
from mimeparse import parse_mime_type
from pytest_infrahouse import terraform_apply
from yaml import load, Loader

from tests.conftest import TERRAFORM_ROOT_DIR


def write_terraform_tf(module_dir: str, aws_provider_version: str) -> None:
    """Write terraform.tf with the specified AWS provider version."""
    with open(f"{module_dir}/terraform.tf", "w") as fp:
        fp.write(
            f"""
            terraform {{
                required_version = "~> 1.0"
                required_providers {{
                    aws = {{
                      source  = "hashicorp/aws"
                      version = "{aws_provider_version}"
                    }}
                    cloudinit = {{
                      source  = "hashicorp/cloudinit"
                        version = "~> 2.3"
                    }}
                  }}
                }}
            """
        )


def parse_userdata(tf_output: dict[str, Any]) -> dict[str, Any]:
    """Decode and parse userdata from terraform output."""
    userdata = b64decode(tf_output["userdata"]["value"]).decode()
    yaml_userdata = (
        parse_mime_type(userdata)[2]["boundary"]
        .split("#cloud-config")[1]
        .replace("--MIMEBOUNDARY--", "")
    )
    return load(yaml_userdata, Loader=Loader)


@pytest.mark.parametrize(
    "aws_provider_version", ["~> 5.11", "~> 6.0"], ids=["aws-5", "aws-6"]
)
def test_module(aws_provider_version, keep_after):
    module_dir = osp.join(TERRAFORM_ROOT_DIR, "apt_source")

    # Delete .terraform.lock.hcl to allow provider version changes
    lock_file_path = osp.join(module_dir, ".terraform.lock.hcl")
    try:
        remove(lock_file_path)
    except FileNotFoundError:
        pass

    write_terraform_tf(module_dir, aws_provider_version)

    with open(osp.join(module_dir, "terraform.tfvars"), "w") as fp:
        fp.write("")

    with terraform_apply(
        module_dir,
        destroy_after=not keep_after,
        json_output=True,
    ) as tf_output:
        userdata = b64decode(tf_output["userdata"]["value"]).decode()
        assert userdata
        print(userdata)
        ud_obj = parse_userdata(tf_output)
        print(json.dumps(ud_obj, indent=4))
        # Verify a string in this command
        # "echo 'W3siYXV0aEZyb20iOiJiYXItc2VjcmV0LWFybiIsIm1hY2hpbmUiOiJiYXIifV0=' > /var/tmp/apt-auth.json.b64",
        assert json.loads(
            b64decode(ud_obj["bootcmd"][0].split()[1].strip("'")).decode()
        ) == [{"machine": "bar", "authFrom": "bar-secret-arn"}]


@pytest.mark.parametrize("aws_provider_version", ["~> 5.11", "~> 6.0"])
@pytest.mark.parametrize(
    "key_config,expected_fields",
    [
        pytest.param(
            {
                "key": "-----BEGIN PGP PUBLIC KEY BLOCK-----\\ntest\\n-----END PGP PUBLIC KEY BLOCK-----"
            },
            {"key"},
            id="embedded_key",
        ),
        pytest.param(
            {"keyid": "A627B7760019BA51B903453D37A181B689AD619"},
            {"keyid"},
            id="keyid_only",
        ),
        pytest.param(
            {
                "keyid": "A627B7760019BA51B903453D37A181B689AD619",
                "keyserver": "keyserver.ubuntu.com",
            },
            {"keyid", "keyserver"},
            id="keyid_with_keyserver",
        ),
    ],
)
def test_extra_repos_key_types(
    aws_provider_version: str,
    key_config: dict[str, str],
    expected_fields: set[str],
    keep_after: bool,
) -> None:
    """Test that extra_repos correctly handles key, keyid, and keyserver options."""
    # Use separate test_keyid directory to avoid modifying apt_source/main.tf
    module_dir = osp.join(TERRAFORM_ROOT_DIR, "test_keyid")

    # Delete .terraform.lock.hcl to allow provider version changes
    lock_file_path = osp.join(module_dir, ".terraform.lock.hcl")
    try:
        remove(lock_file_path)
    except FileNotFoundError:
        pass

    write_terraform_tf(module_dir, aws_provider_version)

    # Build the key configuration string for HCL
    key_hcl_parts = []
    for field, value in key_config.items():
        key_hcl_parts.append(f'{field} = "{value}"')
    key_hcl = "\n      ".join(key_hcl_parts)

    # Write main.tf with the test configuration
    main_tf = dedent(
        f"""\
        module "test" {{
          source      = "../../"
          environment = "dev"
          role        = "foo"
          extra_repos = {{
            "test-repo" = {{
              source = "deb [signed-by=$KEY_FILE] https://example.com/ubuntu noble main"
              {key_hcl}
            }}
          }}
        }}
    """
    )
    with open(osp.join(module_dir, "main.tf"), "w") as fp:
        fp.write(main_tf)

    with open(osp.join(module_dir, "terraform.tfvars"), "w") as fp:
        fp.write("")

    with terraform_apply(
        module_dir,
        destroy_after=not keep_after,
        json_output=True,
    ) as tf_output:
        ud_obj = parse_userdata(tf_output)
        print(json.dumps(ud_obj, indent=4))

        # Verify apt.sources contains the test-repo with expected fields
        apt_sources = ud_obj.get("apt", {}).get("sources", {})
        assert (
            "test-repo" in apt_sources
        ), f"test-repo not found in apt.sources: {apt_sources}"

        repo_config = apt_sources["test-repo"]
        assert "source" in repo_config, "source field missing from repo config"

        # Verify expected key fields are present
        for field in expected_fields:
            assert (
                field in repo_config
            ), f"Expected field '{field}' not in repo config: {repo_config}"

        # Verify unexpected key fields are NOT present
        all_key_fields = {"key", "keyid", "keyserver"}
        unexpected_fields = (
            all_key_fields - expected_fields - {"keyserver"}
        )  # keyserver is optional
        for field in unexpected_fields:
            if field in repo_config:
                pytest.fail(
                    f"Unexpected field '{field}' found in repo config: {repo_config}"
                )
