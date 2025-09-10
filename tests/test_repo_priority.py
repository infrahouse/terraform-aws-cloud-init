import json
from base64 import b64decode
from os import path as osp, remove
from shutil import rmtree
from textwrap import dedent

import pytest
from mimeparse import parse_mime_type
from pytest_infrahouse import terraform_apply
from yaml import load, Loader


@pytest.mark.parametrize(
    "aws_provider_version", ["~> 5.11", "~> 6.0"], ids=["aws-5", "aws-6"]
)
def test_module(aws_provider_version, keep_after):
    terraform_dir = "test_data"
    module_dir = osp.join(terraform_dir, "test_module")

    # Delete .terraform directory and .terraform.lock.hcl to allow provider version changes
    terraform_dir_path = osp.join(module_dir, ".terraform")
    lock_file_path = osp.join(module_dir, ".terraform.lock.hcl")

    try:
        rmtree(terraform_dir_path)
    except FileNotFoundError:
        pass

    try:
        remove(lock_file_path)
    except FileNotFoundError:
        pass

    # Update provider version
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

    with terraform_apply(
        module_dir,
        destroy_after=not keep_after,
        json_output=True,
    ) as tf_output:
        userdata = b64decode(tf_output["userdata"]["value"]).decode()
        assert userdata
        yaml_userdata = (
            parse_mime_type(userdata)[2]["boundary"]
            .split("#cloud-config")[1]
            .replace("--MIMEBOUNDARY--", "")
        )
        ud_obj = load(yaml_userdata, Loader=Loader)
        print(json.dumps(ud_obj, indent=4))
        assert (
            {
                "content": dedent(
                    """
                    Package: *
                    Pin: origin "bar.com"
                    Pin-Priority: 999
                    """
                ),
                "path": "/etc/apt/preferences.d/bar.com.pref",
                "permissions": "0644",
            }
            in ud_obj["write_files"]
        )
