import logging

from infrahouse_core.logging import setup_logging

LOG = logging.getLogger()
TEST_ZONE = "ci-cd.infrahouse.com"
TERRAFORM_ROOT_DIR = "test_data"

setup_logging(LOG, debug=False)
