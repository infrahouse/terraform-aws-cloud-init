import json
from base64 import b64decode
from os import path as osp
from pprint import pprint
from textwrap import dedent

import pytest
from infrahouse_toolkit.terraform import terraform_apply
from mimeparse import parse_mime_type
from yaml import load, Loader

from tests.conftest import (
    LOG,
    TRACE_TERRAFORM,
    DESTROY_AFTER,
)


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
def test_module(mounts, expected_mounts):
    terraform_dir = "test_data"
    module_dir = osp.join(terraform_dir, "test_module")

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
        destroy_after=DESTROY_AFTER,
        json_output=True,
        enable_trace=TRACE_TERRAFORM,
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
