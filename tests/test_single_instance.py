import json
from os import path as osp
from textwrap import dedent
from time import sleep, time

import pytest
from infrahouse_core.aws.ec2_instance import EC2Instance
from infrahouse_core.timeout import timeout
from infrahouse_toolkit.terraform import terraform_apply

from tests.conftest import (
    LOG,
    TERRAFORM_ROOT_DIR,
)


@pytest.mark.parametrize("ami_vendor", ["ubuntu", "infrahouse"])
def test_module(
    service_network,
    test_role_arn,
    keep_after,
    aws_region,
    ami_vendor,
):
    subnet_private_id = service_network["subnet_private_ids"]["value"][0]

    terraform_module_dir = osp.join(TERRAFORM_ROOT_DIR, "single_instance")
    with open(osp.join(terraform_module_dir, "terraform.tfvars"), "w") as fp:
        fp.write(
            dedent(
                f"""
                    region     = "{aws_region}"
                    subnet_id  = "{subnet_private_id}"
                    ami_vendor = "{ami_vendor}"
                    """
            )
        )
        if test_role_arn:
            fp.write(
                dedent(
                    f"""
                    role_arn        = "{test_role_arn}"
                    """
                )
            )

    with terraform_apply(
        terraform_module_dir,
        json_output=True,
        destroy_after=not keep_after,
    ) as tf_output:
        LOG.info("%s", json.dumps(tf_output, indent=4))
        instance_id = tf_output["instance_id"]["value"]
        instance = EC2Instance(instance_id, role_arn=test_role_arn)
        prov_start = time()
        with timeout(900):
            while True:
                cout, cerr = (None, None)
                try:
                    for cmd in ["ls /tmp/puppet-done", "ih-aws --version"]:
                        LOG.info("Sending command: %s to %s", cmd, instance_id)
                        exit_code, cout, cerr = instance.execute_command(cmd)
                        assert exit_code == 0
                    break
                except AssertionError as err:
                    LOG.error("%s failed with %s", cmd, err)
                    LOG.error("STDOUT: %s", cout)
                    LOG.error("STDERR: %s", cerr)
                    sleep(5)
        prov_end = time()
        LOG.info(
            "Instance %s (%s) processed in %f seconds",
            instance_id,
            ami_vendor,
            prov_end - prov_start,
        )
