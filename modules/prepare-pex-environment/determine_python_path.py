from __future__ import print_function
import argparse
import json
import os
import platform
import sys


IS_WIN = platform.system() == "Windows"


DESCRIPTION = """
Script to add PEX and module directory to the PYTHONPATH so that the included packages can be imported by the underlying
command.

This script takes care of Windows long paths by using the short path name.

This script is intended to be run as a terraform data source. As such, the output is a json:

\b
{
    "python_path": "PYTHONPATH value"
}

The paths to add are:
    - The PEX file itself. This is a zipfile that contains a bunch of modules.
    - The PEX file + .bootstrap. This directory contains bootstrapping packages for the pex file.
    - The module path.
"""


def main():
    args = parse_args()
    pex_abspath = os.path.abspath(args.pex)
    pex_bootstrap_path = os.path.join(pex_abspath, ".bootstrap")
    module_abspath = os.path.abspath(args.module_path)
    separator = ":"
    if IS_WIN:
        pex_abspath = windows_long_path(pex_abspath)
        pex_bootstrap_path = windows_long_path(pex_bootstrap_path)
        module_abspath = windows_long_path(module_abspath)
        separator = ";"

    python_path = [module_abspath, pex_abspath, pex_bootstrap_path] + sys.path
    out = {"python_path": separator.join(python_path)}
    # Terraform data source expects a json output to stdout
    print(json.dumps(out))


def parse_args():
    """ Prepare the parser for the CLI. """
    parser = argparse.ArgumentParser(
        description=DESCRIPTION
    )
    parser.add_argument(
        "--pex",
        required=True,
        help="PEX file that the PYTHONPATH should be prepared for.",
    )
    parser.add_argument(
        "--module-path",
        required=True,
        help="Path to the module that contains the python package that the PYTHONPATH should be prepared for.",
    )
    return parser.parse_args()


def add_to_python_path(original, new_path):
    """
    Add the new_path to the original PYTHONPATH and return the new value.
    """
    if not original:
        # original value doesn't exist, so we just use the new path as the starting point
        return new_path

    separator = ";" if IS_WIN else ":"
    return new_path + separator + original


def windows_long_path(path):
    # Windows has a max path length:
    # https://docs.microsoft.com/en-us/windows/desktop/FileIO/naming-a-file#maximum-path-length-limitation
    # We work around this by using the short path API that windows provides
    assert IS_WIN

    # We use the GetShortPathNameW kernel API from windows to get the short path form of a long path so that we can
    # access it without hitting the limit.
    # See https://stackoverflow.com/a/23598461
    import ctypes
    from ctypes import wintypes
    _GetShortPathNameW = ctypes.windll.kernel32.GetShortPathNameW
    _GetShortPathNameW.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
    _GetShortPathNameW.restype = wintypes.DWORD

    output_buf_size = 0
    # NOTE: this is a do while loop (exit condition checked at end of loop), because the condition needs to be checked
    # after the API call.
    while True:
        output_buf = ctypes.create_unicode_buffer(output_buf_size)
        needed = _GetShortPathNameW(path, output_buf, output_buf_size)
        if output_buf_size >= needed:
            return output_buf.value
        else:
            output_buf_size = needed


if __name__ == "__main__":
    main()
