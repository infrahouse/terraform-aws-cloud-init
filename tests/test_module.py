import json
from base64 import b64decode

import pytest
from infrahouse_toolkit.terraform import terraform_apply

from tests.conftest import (
    LOG,
    TRACE_TERRAFORM,
    DESTROY_AFTER,
)


def test_module():
    terraform_dir = "test_data/test_module"

    with terraform_apply(
        terraform_dir,
        destroy_after=DESTROY_AFTER,
        json_output=True,
        enable_trace=TRACE_TERRAFORM,
    ) as tf_output:
        print(b64decode(tf_output["userdata"]["value"]).decode())
        assert b64decode(tf_output["userdata"]["value"])
