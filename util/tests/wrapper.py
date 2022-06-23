import pathlib
import sys

import pytest

from util.tests.fixtures import fixtures

if __name__ == "__main__":
    test_files = pathlib.Path(__file__).parent.parent.parent.glob("**/test*.py")
    print([str(x) for x in test_files if "common" in x.parts()])
    if sys.argv[1] != "--ignore":
        test_files = list()
        whitelist = sys.argv[1].split(",")
        for partial in whitelist:
            test_files.extend([str(f) for f in test_files if partial in str(f)])
    sys.exit(pytest.main(sys.argv[1:], plugins=[fixtures]))
