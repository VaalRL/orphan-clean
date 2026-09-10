#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
orphan-clean Desktop Application Entrypoint
"""
import sys
from pathlib import Path

# Ensure package directory is in sys.path
root_dir = Path(__file__).resolve().parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from orphanclean.gui import run_server

if __name__ == "__main__":
    run_server()
