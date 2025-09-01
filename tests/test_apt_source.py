import json
from base64 import b64decode
from os import path as osp, remove

import pytest
from mimeparse import parse_mime_type
from pytest_infrahouse import terraform_apply
from yaml import load, Loader

from tests.conftest import TERRAFORM_ROOT_DIR


@pytest.mark.parametrize("aws_provider_version", ["~> 5.11", "~> 6.0"])
def test_module(aws_provider_version, keep_after):
    module_dir = osp.join(TERRAFORM_ROOT_DIR, "apt_source")

    # Delete .terraform.lock.hcl to allow provider version changes
    lock_file_path = osp.join(module_dir, ".terraform.lock.hcl")
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
        yaml_userdata = (
            parse_mime_type(userdata)[2]["boundary"]
            .split("#cloud-config")[1]
            .replace("--MIMEBOUNDARY--", "")
        )
        ud_obj = load(yaml_userdata, Loader=Loader)
        print(json.dumps(ud_obj, indent=4))
        # Verify a string in this command
        # "echo 'W3siYXV0aEZyb20iOiJiYXItc2VjcmV0LWFybiIsIm1hY2hpbmUiOiJiYXIifV0=' > /var/tmp/apt-auth.json.b64",
        assert json.loads(
            b64decode(ud_obj["bootcmd"][0].split()[1].strip("'")).decode()
        ) == [{"machine": "bar", "authFrom": "bar-secret-arn"}]
