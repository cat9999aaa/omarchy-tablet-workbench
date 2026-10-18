#!/usr/bin/python3
"""Restore an exact recorded file publication; runtime takeover has a separate guard."""
import argparse
import json
from pathlib import Path
from install import Installer
p=argparse.ArgumentParser();p.add_argument('transaction');a=p.parse_args()
print(json.dumps(Installer(Path.home()).rollback(a.transaction)))
