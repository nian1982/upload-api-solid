import importlib
import sys

import pytest


@pytest.fixture(autouse=True)
def _clean_logger():
    sys.modules.pop("shared.logger", None)
    yield
    sys.modules.pop("shared.logger", None)
