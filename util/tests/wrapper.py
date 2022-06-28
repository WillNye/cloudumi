import os
import pathlib
import sys

import pytest

from util.tests.fixtures import fixtures


class bcolors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


if __name__ == "__main__":
    blacklist = ["external"]
    test_files = pathlib.Path(__file__).parent.parent.parent.glob("**/test*.py")
    if len(sys.argv) == 2:
        whitelist = sys.argv[1].split(",")
    else:
        whitelist = list()
    filtered_test_files = list()

    profile_path = pathlib.Path(os.getenv("HOME"))
    cache_dir_index = profile_path.parts.index(".cache")
    home_dir = profile_path.parents[len(profile_path.parents) - cache_dir_index]
    os.environ["HOME"] = str(home_dir)

    for path in test_files:
        if not path.name.startswith("test_"):
            continue
        found = 0
        ignore = False
        for partial in blacklist:
            if partial in path.parts:
                ignore = True
                break
        if not ignore:
            for partial in whitelist:
                if partial in path.parts:
                    found += 1
        if found == len(whitelist):
            filtered_test_files.append(str(path.parents[0]))

    if filtered_test_files:
        sys.exit(pytest.main(list(set(filtered_test_files)), plugins=[fixtures]))
    else:
        print(f"\n\n{bcolors.WARNING}No tests found{bcolors.ENDC}\n\n")
        sys.exit()
