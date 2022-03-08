import sys

import pytest
from fixtures import conftest

if __name__ == "__main__":
    sys.exit(pytest.main(sys.argv[1:], plugins=[conftest]))
