import json
from base64 import b64decode
from os import path as osp, remove
from pprint import pprint
from shutil import rmtree
from textwrap import dedent

import pytest
from mimeparse import parse_mime_type
from pytest_infrahouse import terraform_apply
from yaml import load, Loader

from tests.conftest import TERRAFORM_ROOT_DIR


@pytest.mark.parametrize("aws_provider_version", ["~> 5.11", "~> 6.0"])
@pytest.mark.parametrize(
    "puppet_manifest, expected_fact, expected_runcmd",
    [
        (
            None,
            "/opt/puppet-code/environments/dev/manifests/site.pp",
            [
                "ih-puppet",
                "",
                "--environment",
                "dev",
                "--environmentpath",
                "{root_directory}/environments",
                "--root-directory",
                "/opt/puppet-code",
                "--hiera-config",
                "{root_directory}/environments/{environment}/hiera.yaml",
                "--module-path",
                "{root_directory}/modules",
                "apply",
                "/opt/puppet-code/environments/dev/manifests/site.pp",
            ],
        ),
        (
            "boo",
            "boo",
            [
                "ih-puppet",
                "",
                "--environment",
                "dev",
                "--environmentpath",
                "{root_directory}/environments",
                "--root-directory",
                "/opt/puppet-code",
                "--hiera-config",
                "{root_directory}/environments/{environment}/hiera.yaml",
                "--module-path",
                "{root_directory}/modules",
                "apply",
                "boo",
            ],
        ),
    ],
)
def test_module(aws_provider_version, puppet_manifest, expected_fact, expected_runcmd, keep_after):
    module_dir = osp.join(TERRAFORM_ROOT_DIR, "test_module")

    # Delete .terraform directory and .terraform.lock.hcl to allow provider version changes
    terraform_dir = osp.join(module_dir, ".terraform")
    lock_file_path = osp.join(module_dir, ".terraform.lock.hcl")
    
    try:
        rmtree(terraform_dir)
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
        value = f'"{puppet_manifest}"' if puppet_manifest else "null"
        fp.write(
            dedent(
                f"""
                puppet_manifest = { value }
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
        found_ih_puppet_json = False
        for file_def in ud_obj["write_files"]:
            if file_def["path"] == "/etc/puppetlabs/facter/facts.d/ih-puppet.json":
                found_ih_puppet_json = True
                facts = json.loads(file_def["content"])
                pprint(facts)
                assert facts["ih-puppet"]["manifest"] == expected_fact
        assert found_ih_puppet_json
        assert ud_obj["runcmd"][-1].split(" ") == expected_runcmd
