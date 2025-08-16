import json
from base64 import b64decode
from os import path as osp
from pprint import pprint
from textwrap import dedent

import pytest
from mimeparse import parse_mime_type
from pytest_infrahouse import terraform_apply
from yaml import load, Loader


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
def test_module(puppet_manifest, expected_fact, expected_runcmd, keep_after):
    terraform_dir = "test_data"
    module_dir = osp.join(terraform_dir, "test_module")

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
