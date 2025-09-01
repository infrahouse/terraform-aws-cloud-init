import json
from base64 import b64decode
from os import path as osp, remove
from shutil import rmtree
from textwrap import dedent

import pytest
from mimeparse import parse_mime_type
from pytest_infrahouse import terraform_apply
from yaml import load, Loader


@pytest.mark.parametrize("aws_provider_version", ["~> 5.11", "~> 6.0"])
@pytest.mark.parametrize(
    "mounts, expected_mounts",
    [
        (
            json.dumps(
                [
                    [
                        "file_system_id.efs.aws-region.amazonaws.com:/",
                        "mount_point",
                        "nfs4",
                        "nfsvers=4.1,rsize=1048576,wsize=1048576,hard,timeo=600,retrans=2,noresvport,_netdev",
                        "0",
                        "0",
                    ],
                    ["xvdh", "/opt/data", "auto", "defaults,nofail", "0", "0"],
                ],
                indent=4,
            ),
            [
                [
                    "file_system_id.efs.aws-region.amazonaws.com:/",
                    "mount_point",
                    "nfs4",
                    "nfsvers=4.1,rsize=1048576,wsize=1048576,hard,timeo=600,retrans=2,noresvport,_netdev",
                    "0",
                    "0",
                ],
                ["xvdh", "/opt/data", "auto", "defaults,nofail", "0", "0"],
            ],
        ),
        (None, None),
    ],
)
def test_module(aws_provider_version, mounts, expected_mounts, keep_after):
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

    with open(osp.join(module_dir, "terraform.tfvars"), "w") as fp:
        fp.write(
            dedent(
                f"""
                mounts = {mounts or "null"}
                """
            )
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
        if mounts:
            assert ud_obj["mounts"] == expected_mounts
        else:
            assert "mounts" not in ud_obj
