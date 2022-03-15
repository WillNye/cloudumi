import sys

import pytest

from util.tests.fixtures import fixtures

if __name__ == "__main__":
    sys.exit(pytest.main(sys.argv[1:], plugins=[fixtures]))
