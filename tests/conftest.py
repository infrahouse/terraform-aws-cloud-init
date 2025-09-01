import logging

from infrahouse_core.logging import setup_logging

LOG = logging.getLogger()
TERRAFORM_ROOT_DIR = "test_data"

setup_logging(LOG, debug=False)
