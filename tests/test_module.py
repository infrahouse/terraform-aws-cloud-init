import json
from base64 import b64decode
from os import path as osp, remove
from shutil import rmtree
from textwrap import dedent

import pytest
from mimeparse import parse_mime_type
from pytest_infrahouse import terraform_apply
from yaml import load, Loader


@pytest.mark.parametrize("aws_provider_version", ["~> 6.0"], ids=["aws-6"])
@pytest.mark.parametrize(
    "mounts, expected_mounts, expected_mount_packages, forbidden_mount_packages",
    [
        # NFS mount plus a plain EBS mount: nfs-common must be injected,
        # cifs-utils must not be.
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
            ["nfs-common"],
            ["cifs-utils"],
        ),
        # Two NFS mounts: nfs-common must appear exactly once (distinct()).
        (
            json.dumps(
                [
                    [
                        "fs-a.efs.aws-region.amazonaws.com:/",
                        "/mnt/a",
                        "nfs4",
                        "defaults",
                        "0",
                        "0",
                    ],
                    [
                        "fs-b.efs.aws-region.amazonaws.com:/",
                        "/mnt/b",
                        "nfs4",
                        "defaults",
                        "0",
                        "0",
                    ],
                ],
                indent=4,
            ),
            [
                [
                    "fs-a.efs.aws-region.amazonaws.com:/",
                    "/mnt/a",
                    "nfs4",
                    "defaults",
                    "0",
                    "0",
                ],
                [
                    "fs-b.efs.aws-region.amazonaws.com:/",
                    "/mnt/b",
                    "nfs4",
                    "defaults",
                    "0",
                    "0",
                ],
            ],
            ["nfs-common"],
            ["cifs-utils"],
        ),
        # CIFS mount: cifs-utils must be injected, nfs-common must not be.
        (
            json.dumps(
                [
                    ["//server/share", "/mnt/share", "cifs", "defaults", "0", "0"],
                ],
                indent=4,
            ),
            [
                ["//server/share", "/mnt/share", "cifs", "defaults", "0", "0"],
            ],
            ["cifs-utils"],
            ["nfs-common"],
        ),
        # Plain EBS mount only: no mount client packages should be added.
        (
            json.dumps(
                [
                    ["xvdh", "/opt/data", "auto", "defaults,nofail", "0", "0"],
                ],
                indent=4,
            ),
            [
                ["xvdh", "/opt/data", "auto", "defaults,nofail", "0", "0"],
            ],
            [],
            ["nfs-common", "cifs-utils"],
        ),
        (None, None, [], ["nfs-common", "cifs-utils"]),
    ],
)
def test_module(
    aws_provider_version,
    mounts,
    expected_mounts,
    expected_mount_packages,
    forbidden_mount_packages,
    keep_after,
):
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
        fp.write(f"""
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
            """)

    with open(osp.join(module_dir, "terraform.tfvars"), "w") as fp:
        fp.write(dedent(f"""
                mounts = {mounts or "null"}
                """))

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

        packages = ud_obj.get("packages", [])
        for pkg in expected_mount_packages:
            assert (
                pkg in packages
            ), f"expected mount client package '{pkg}' in packages, got: {packages}"
            # distinct() in locals.tf must collapse duplicates.
            assert (
                packages.count(pkg) == 1
            ), f"expected '{pkg}' exactly once, got {packages.count(pkg)} in {packages}"
        for pkg in forbidden_mount_packages:
            assert (
                pkg not in packages
            ), f"unexpected mount client package '{pkg}' in packages: {packages}"

        # apt-daily / unattended-upgrades must be stopped and masked before any
        # apt-touching step runs, so they cannot race for the dpkg lock
        # (see issue #87).
        bootcmd = ud_obj["bootcmd"]
        assert bootcmd[0].startswith(
            "systemctl stop apt-daily"
        ), f"expected bootcmd to start with systemctl stop of apt-daily units, got: {bootcmd[0]}"
        assert bootcmd[1].startswith(
            "systemctl mask apt-daily"
        ), f"expected bootcmd[1] to mask apt-daily units, got: {bootcmd[1]}"
        for unit in (
            "apt-daily.service",
            "apt-daily.timer",
            "apt-daily-upgrade.service",
            "apt-daily-upgrade.timer",
            "unattended-upgrades.service",
        ):
            assert unit in bootcmd[0], f"{unit} missing from stop command: {bootcmd[0]}"
            assert unit in bootcmd[1], f"{unit} missing from mask command: {bootcmd[1]}"
