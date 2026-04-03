#!/usr/bin/env python3
"""
CLIC — Cooler Lite IDE for Commandline

    python run.py
    python run.py --dir /path/to/project
    python run.py --no-sound
"""

import argparse
import os
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(prog="clic", description="CLIC — Zen terminal")
    parser.add_argument("--dir", "-d", type=str, default=None)
    parser.add_argument("--no-sound", action="store_true")
    args = parser.parse_args()

    if args.dir:
        target = Path(args.dir).resolve()
        if target.is_dir():
            os.chdir(target)
        else:
            print(f"Error: {args.dir} is not a valid directory", file=sys.stderr)
            sys.exit(1)

    from clic.config import Config
    Config.load()

    if args.no_sound:
        Config.set("sounds", "enabled", value=False)

    from clic.app import run
    run()


if __name__ == "__main__":
    main()
