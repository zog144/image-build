"""Maintained build workers; historical deployment handoffs are not entry points."""
import argparse
import importlib
import sys

from .worker_contracts import modules

WORKERS = modules()

def main(argv=None):
    arguments = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("worker", choices=WORKERS)
    parser.add_argument("arguments", nargs=argparse.REMAINDER)
    options = parser.parse_args(arguments)
    previous = sys.argv
    try:
        sys.argv = ["image-build-worker " + options.worker, *options.arguments]
        return importlib.import_module(WORKERS[options.worker]).main()
    finally:
        sys.argv = previous

if __name__ == "__main__":
    main()
