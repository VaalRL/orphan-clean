#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
orphan-clean: Command-Line Interface
Author: Knowledge-trend-research
License: MIT
"""

import sys
import argparse
from pathlib import Path
from typing import List

from . import __version__
from .core import LocalDependencyMatcher, normalize_name, CORE_PROTECTED_PACKAGES
from .gui import run_server

BANNER = r"""
  ___             _                      ____ _                  
 / _ \ _ __ _ __ | |__   __ _ _ __      / ___| | ___  __ _ _ __  
| | | | '__| '_ \| '_ \ / _` | '_ \ ___| |   | |/ _ \/ _` | '_ \ 
| |_| | |  | |_) | | | | (_| | | | |___| |___| |  __/ (_| | | | |
 \___/|_|  | .__/|_| |_|\__,_|_| |_|    \____|_|\___|\__,_|_| |_|
           |_|                                                   
   [ Polyglot Dependency Auditor & Safe Orphan Cleaner v1.0 ]
"""

def print_banner():
    print(BANNER)

def main():
    parser = argparse.ArgumentParser(
        prog="orphan-clean",
        description="orphan-clean: Polyglot Dependency Auditor & Safe Orphan Cleaner"
    )
    parser.add_argument("path", nargs="?", default=None,
                        help="Target directory to audit (default: current directory)")
    parser.add_argument("--orphans", action="store_true",
                        help="Display 3-tier orphan package classification")
    parser.add_argument("--clean-orphans", action="store_true",
                        help="Safely backup and batch uninstall Tier 3 orphan packages")
    parser.add_argument("--export-orphans", nargs="?", const="orphans_to_remove.txt",
                        help="Export Tier 3 orphan packages to text file")
    parser.add_argument("--low-freq", type=int, metavar="N",
                        help="List packages used by N or fewer projects")
    parser.add_argument("--bloat", action="store_true",
                        help="Scan for Rust target/ and Flutter build/ bloat")
    parser.add_argument("--clean-bloat", action="store_true",
                        help="Safely clean detected build bloat directories")
    parser.add_argument("--gui", action="store_true",
                        help="Launch the interactive Web GUI dashboard")
    parser.add_argument("-p", "--port", type=int, default=8765,
                        help="Port for GUI dashboard server (default: 8765)")
    parser.add_argument("-v", "--version", action="version",
                        version=f"orphan-clean {__version__}")

    args = parser.parse_args()

    # If invoked with 'gui' positional argument or --gui flag, run GUI
    if args.gui or (args.path == "gui"):
        run_server(port=args.port)
        return

    # If no path specified and no specific action, launch GUI by default
    if args.path is None and not (args.orphans or args.clean_orphans or args.bloat):
        print_banner()
        print("[*] No path or arguments provided. Launching orphan-clean GUI dashboard...")
        run_server(port=args.port)
        return

    scan_path = args.path or "."
    print_banner()
    print(f"[*] Auditing workspace: {Path(scan_path).resolve()}")

    matcher = LocalDependencyMatcher(scan_path)
    projects = matcher.scan()
    print(f"[*] Found {len(projects)} projects.")

    orphans_info = matcher.classify_orphans()

    # --orphans
    if args.orphans or args.clean_orphans or args.export_orphans:
        print("\n" + "=" * 60)
        print("  ORPHAN PACKAGES AUDIT & CLASSIFICATION REPORT")
        print("=" * 60)
        print(f"Total Installed Python Packages : {orphans_info['total_installed']}")
        print(f"Declared in Scanned Projects    : {orphans_info['declared_count']}")
        print(f"Active or Transitive (In-Use)   : {orphans_info['active_or_transitive_count']}")
        print(f"Unreferenced Packages           : {orphans_info['unreferenced_count']}")

        print(f"\n--- [Tier 1: Core System Packages (FORBIDDEN from uninstallation)] ({len(orphans_info['tier1_protected'])}) ---")
        for p in orphans_info["tier1_protected"]:
            print(f"  [LOCKED] {p['name']} ({p['version']})")

        print(f"\n--- [Tier 2: Developer Tooling & CLI Utilities (Review Advised)] ({len(orphans_info['tier2_cli_tools'])}) ---")
        for p in orphans_info["tier2_cli_tools"]:
            print(f"  [TOOL]   {p['name']} ({p['version']})")

        print(f"\n--- [Tier 3: Pure Isolated Libraries (Safe to Clean)] ({len(orphans_info['tier3_pure_libraries'])}) ---")
        for p in orphans_info["tier3_pure_libraries"]:
            req_str = f" [needed by: {', '.join(p['required_by'])}]" if p["required_by"] else ""
            print(f"  [CLEAN]  {p['name']} ({p['version']}){req_str}")

    # --export-orphans
    if args.export_orphans:
        out_file = Path(args.export_orphans)
        tier3_names = [p["name"] for p in orphans_info["tier3_pure_libraries"]]
        with open(out_file, "w", encoding="utf-8") as f:
            for n in tier3_names:
                f.write(f"{n}\n")
        print(f"\n[+] Exported {len(tier3_names)} safe-to-clean packages to: {out_file.resolve()}")

    # --clean-orphans
    if args.clean_orphans:
        tier3_pkgs = [p["name"] for p in orphans_info["tier3_pure_libraries"]]
        if not tier3_pkgs:
            print("\n[+] No Tier 3 orphan packages to clean. Your environment is clean!")
            return

        print(f"\n[!] Identified {len(tier3_pkgs)} Tier 3 orphan packages ready for safe removal.")
        choice = input(f"[?] Proceed with automatic backup and uninstall of {len(tier3_pkgs)} packages? (y/N): ").strip().lower()
        if choice == "y":
            print("[*] Creating pip freeze safety backup snapshot...")
            res = matcher.uninstall_packages(tier3_pkgs, backup=True)
            if res["success"]:
                print(f"[+] Successfully uninstalled {len(res['uninstalled'])} packages!")
                print(f"[+] Backup snapshot saved to: {res['backup_file']}")
                print(f"[*] To rollback, run: pip install -r \"{res['backup_file']}\"")
            else:
                print(f"[-] Uninstallation failed: {res.get('error') or res.get('stderr')}")
        else:
            print("[-] Operation aborted by user.")

    # --bloat
    if args.bloat or args.clean_bloat:
        bloat_list = matcher.scan_bloat()
        print("\n" + "=" * 60)
        print("  BUILD BLOAT AUDIT (Rust target/ & Flutter build/)")
        print("=" * 60)
        if not bloat_list:
            print("  No reclaimable build bloat directories found.")
        else:
            total_mb = sum(b["size_mb"] for b in bloat_list)
            for b in bloat_list:
                print(f"  [{b['ecosystem']}] {b['project']}: {b['size_mb']} MB -> {b['path']}")
            print(f"\nTotal reclaimable bloat: {total_mb:.1f} MB (approx {total_mb/1024:.2f} GB)")

            if args.clean_bloat:
                c = input(f"[?] Clean all {len(bloat_list)} build bloat directories? (y/N): ").strip().lower()
                if c == "y":
                    for b in bloat_list:
                        r = matcher.clean_bloat_target(b["path"])
                        if r["success"]:
                            print(f"  [+] Cleaned: {b['path']}")
                        else:
                            print(f"  [-] Failed to clean {b['path']}: {r['error']}")
                else:
                    print("[-] Operation aborted.")

    # --low-freq
    if args.low_freq is not None:
        print(f"\n--- Packages used by <= {args.low_freq} projects ---")
        for pkg, usages in matcher.inverted_index.items():
            if len(usages) <= args.low_freq:
                projs = ", ".join([u["project"] for u in usages])
                print(f"  {pkg} ({len(usages)} projects: {projs})")

if __name__ == "__main__":
    main()
