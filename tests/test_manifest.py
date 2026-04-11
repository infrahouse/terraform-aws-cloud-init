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


@pytest.mark.parametrize("aws_provider_version", ["~> 6.0"])
@pytest.mark.parametrize(
    "puppet_manifest, expected_fact, expected_runcmd",
    [
        (
            None,
            "/opt/puppet-code/environments/dev/manifests/site.pp",
            [
                "ih-puppet",
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
def test_module(
    aws_provider_version, puppet_manifest, expected_fact, expected_runcmd, keep_after
):
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
        value = f'"{puppet_manifest}"' if puppet_manifest else "null"
        fp.write(dedent(f"""
                puppet_manifest = { value }
                lifecycle_hook_name = null
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
        found_ih_puppet_json = False
        bootstrap_script = None
        for file_def in ud_obj["write_files"]:
            if file_def["path"] == "/etc/puppetlabs/facter/facts.d/ih-puppet.json":
                found_ih_puppet_json = True
                facts = json.loads(file_def["content"])
                pprint(facts)
                assert facts["ih-puppet"]["manifest"] == expected_fact
            if file_def["path"] == "/usr/local/bin/ih-bootstrap":
                bootstrap_script = file_def["content"]
        assert found_ih_puppet_json

        # runcmd is a single entry that invokes the bootstrap script. The
        # script wraps every step under set -euo pipefail so cloud-init
        # cannot fail-open between steps.
        assert ud_obj["runcmd"] == ["bash /usr/local/bin/ih-bootstrap"]

        # The bootstrap script must be delivered via write_files with exec
        # permissions and must contain the ih-puppet line plus the truthful
        # /var/run/puppet-done marker on the success path.
        assert bootstrap_script is not None
        assert "set -euo pipefail" in bootstrap_script
        expected_ih_puppet_line = " ".join(expected_runcmd)
        assert expected_ih_puppet_line in bootstrap_script
        assert "touch /var/run/puppet-done" in bootstrap_script


@pytest.mark.parametrize("aws_provider_version", ["~> 6.0"])
def test_lifecycle_hook(aws_provider_version, keep_after):
    """
    When lifecycle_hook_name is set, the bootstrap script must register an
    ERR trap that signals ABANDON on failure and signals CONTINUE on the
    success path, so a broken instance cannot silently join the ASG.
    """
    module_dir = osp.join(TERRAFORM_ROOT_DIR, "test_module")
    hook_name = "bootstrap"

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
                puppet_manifest = null
                lifecycle_hook_name = "{hook_name}"
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

        bootstrap_script = None
        for file_def in ud_obj["write_files"]:
            if file_def["path"] == "/usr/local/bin/ih-bootstrap":
                bootstrap_script = file_def["content"]
        assert bootstrap_script is not None

        # Trap must be defined and registered on ERR so any failing step
        # signals ABANDON to the lifecycle hook before the script exits.
        assert "_ih_signal_abandon()" in bootstrap_script
        assert "trap _ih_signal_abandon ERR" in bootstrap_script

        # Both hook signals must reference the configured hook name.
        abandon_line = (
            f'ih-aws --verbose autoscaling complete "{hook_name}" --result ABANDON'
        )
        continue_line = (
            f'ih-aws --verbose autoscaling complete "{hook_name}" --result CONTINUE'
        )
        assert abandon_line in bootstrap_script
        assert continue_line in bootstrap_script

        # CONTINUE must come after the puppet-done marker so the ASG only
        # sees success once bootstrap has actually completed.
        done_idx = bootstrap_script.index("touch /var/run/puppet-done")
        continue_idx = bootstrap_script.index(continue_line)
        assert continue_idx > done_idx
