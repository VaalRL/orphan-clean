#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
orphan-clean: Core Engine
Author: Knowledge-trend-research
License: MIT
"""

import os
import sys
import json
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any, Optional

try:
    from packaging.specifiers import SpecifierSet
    from packaging.version import Version
    HAS_PACKAGING = True
except ImportError:
    HAS_PACKAGING = False

def normalize_name(name: str) -> str:
    """Normalize package names according to PEP 503."""
    return re.sub(r"[-_.]+", "-", name).strip().lower()

# Tier 1: Protected Core System Packages (FORBIDDEN from uninstallation)
CORE_PROTECTED_PACKAGES = {
    "pip", "setuptools", "wheel", "virtualenv", "packaging",
    "ipykernel", "ipython", "jupyter", "jupyter-core", "jupyter-client",
    "pywin32", "pydantic", "pydantic-core", "mcp", "certifi",
    "urllib3", "charset-normalizer", "idna", "platformdirs",
    "typing-extensions", "colorama", "six", "distlib", "filelock",
    "pip-tools", "wcwidth", "pygments", "prompt-toolkit"
}

# Tier 2: Developer Tooling & CLI Utilities (Review advised)
CLI_OR_TOOL_PACKAGES = {
    "black", "flake8", "mypy", "pytest", "ruff", "twine",
    "pyinstaller", "pyinstaller-hooks-contrib", "pipdeptree",
    "fawltydeps", "coverage", "tox", "nox", "poetry", "pdm",
    "hatch", "invoke", "pre-commit", "bandit", "isort", "autopep8",
    "build", "pylint", "pipreqs"
}

class LocalDependencyMatcher:
    def __init__(self, root_dir: str):
        self.root_dir = Path(root_dir).resolve()
        self.projects: List[Dict[str, Any]] = []
        self.all_declared_python: Set[str] = set()
        self.all_declared_node: Set[str] = set()
        self.inverted_index: Dict[str, List[Dict[str, Any]]] = {}
        
        self.global_python_dists: Dict[str, str] = {}
        self.global_python_requires: Dict[str, List[str]] = {}
        self.global_node_pkgs: Dict[str, str] = {}
        
        self.load_global_environments()

    def load_global_environments(self):
        """Inspect packages installed in Python and Global npm environments."""
        try:
            import importlib.metadata
            for dist in importlib.metadata.distributions():
                raw_name = dist.metadata.get("Name")
                if not raw_name:
                    continue
                name = normalize_name(raw_name)
                self.global_python_dists[name] = dist.version
                
                reqs = []
                if dist.requires:
                    for r in dist.requires:
                        m = re.split(r"(==|>=|<=|>|<|~=|!=|;|\s|\[)", r, maxsplit=1)
                        r_name = normalize_name(m[0])
                        if r_name:
                            reqs.append(r_name)
                self.global_python_requires[name] = reqs
        except Exception as e:
            pass

        try:
            res = subprocess.run(["npm", "list", "-g", "--depth=0", "--json"],
                                 capture_output=True, text=True, timeout=5, shell=sys.platform == "win32")
            if res.returncode == 0:
                data = json.loads(res.stdout)
                for k, v in data.get("dependencies", {}).items():
                    self.global_node_pkgs[k] = v.get("version", "unknown")
        except Exception:
            pass

    def scan(self) -> List[Dict[str, Any]]:
        """Recursively scan root_dir for multi-language projects."""
        self.projects = []
        self.all_declared_python = set()
        self.all_declared_node = set()
        self.inverted_index = {}

        ignore_dirs = {
            ".git", "node_modules", ".venv", "venv", "env", "__pycache__",
            ".pytest_cache", "dist", "build", "target", ".dart_tool",
            "AppData", "$RECYCLE.BIN", "System Volume Information"
        }

        for current_root, dirs, files in os.walk(self.root_dir):
            dirs[:] = [d for d in dirs if d not in ignore_dirs and not d.startswith(".")]
            p_root = Path(current_root)
            
            has_py = any(f in files for f in ["requirements.txt", "pyproject.toml", "setup.py", "Pipfile"])
            if has_py:
                proj = self._parse_python_project(p_root, files)
                if proj:
                    self.projects.append(proj)
                    for dep in proj["declared_deps"]:
                        norm_dep = normalize_name(dep["name"])
                        self.all_declared_python.add(norm_dep)
                        if norm_dep not in self.inverted_index:
                            self.inverted_index[norm_dep] = []
                        self.inverted_index[norm_dep].append({
                            "project": proj["name"],
                            "path": str(proj["path"]),
                            "spec": dep["spec"],
                            "installed": dep.get("installed_version"),
                            "status": dep.get("status")
                        })

            if "package.json" in files:
                proj = self._parse_node_project(p_root)
                if proj:
                    self.projects.append(proj)
                    for dep in proj["declared_deps"]:
                        self.all_declared_node.add(dep["name"])

            if "Cargo.toml" in files:
                proj = self._parse_rust_project(p_root)
                if proj:
                    self.projects.append(proj)

            if "pubspec.yaml" in files:
                proj = self._parse_flutter_project(p_root)
                if proj:
                    self.projects.append(proj)

        return self.projects

    def _parse_python_project(self, path: Path, files: List[str]) -> Optional[Dict[str, Any]]:
        declared = []
        for f in files:
            if f.startswith("requirements") and f.endswith(".txt"):
                try:
                    with open(path / f, "r", encoding="utf-8", errors="ignore") as rf:
                        for line in rf:
                            line = line.strip()
                            if not line or line.startswith("#") or line.startswith("-"):
                                continue
                            parts = re.split(r"(==|>=|<=|>|<|~=|!=)", line, maxsplit=1)
                            pkg = parts[0].strip()
                            spec = parts[1] + parts[2].strip() if len(parts) == 3 else ""
                            if pkg:
                                declared.append({"name": pkg, "spec": spec, "source": f})
                except Exception:
                    pass

        if "pyproject.toml" in files:
            try:
                with open(path / "pyproject.toml", "r", encoding="utf-8", errors="ignore") as pf:
                    in_deps = False
                    for line in pf:
                        line = line.strip()
                        if line.startswith("dependencies = ["):
                            in_deps = True
                            continue
                        if in_deps:
                            if line.endswith("]"):
                                in_deps = False
                                continue
                            clean_line = line.strip('", ')
                            if clean_line:
                                parts = re.split(r"(==|>=|<=|>|<|~=|!=)", clean_line, maxsplit=1)
                                pkg = parts[0].strip()
                                spec = parts[1] + parts[2].strip() if len(parts) == 3 else ""
                                if pkg:
                                    declared.append({"name": pkg, "spec": spec, "source": "pyproject.toml"})
            except Exception:
                pass

        if not declared:
            return None

        local_env = path / ".venv"
        installed_map = self.global_python_dists
        env_type = "Global"

        if local_env.is_dir():
            env_type = "In-Project (.venv)"
            sp = local_env / "Lib" / "site-packages"
            if not sp.is_dir():
                sp_dirs = list(local_env.glob("lib/python*/site-packages"))
                if sp_dirs:
                    sp = sp_dirs[0]
            if sp.is_dir():
                local_installed = {}
                for dist_info in sp.glob("*.dist-info"):
                    meta = dist_info / "METADATA"
                    if meta.is_file():
                        try:
                            with open(meta, "r", encoding="utf-8", errors="ignore") as mf:
                                m_name, m_ver = "", ""
                                for line in mf:
                                    if line.startswith("Name:"):
                                        m_name = line.split(":", 1)[1].strip()
                                    elif line.startswith("Version:"):
                                        m_ver = line.split(":", 1)[1].strip()
                                    if m_name and m_ver:
                                        local_installed[normalize_name(m_name)] = m_ver
                                        break
                        except Exception:
                            pass
                if local_installed:
                    installed_map = local_installed

        for dep in declared:
            norm = normalize_name(dep["name"])
            if norm in installed_map:
                inst_ver = installed_map[norm]
                dep["installed_version"] = inst_ver
                dep["status"] = self._match_version(dep["spec"], inst_ver)
            else:
                dep["installed_version"] = None
                dep["status"] = "MISSING"

        return {
            "name": path.name,
            "ecosystem": "Python",
            "path": str(path),
            "env_type": env_type,
            "declared_deps": declared
        }

    def _parse_node_project(self, path: Path) -> Optional[Dict[str, Any]]:
        pkg_json = path / "package.json"
        try:
            with open(pkg_json, "r", encoding="utf-8", errors="ignore") as f:
                data = json.load(f)
            declared = []
            deps = data.get("dependencies", {})
            dev_deps = data.get("devDependencies", {})
            for k, v in {**deps, **dev_deps}.items():
                declared.append({"name": k, "spec": v, "source": "package.json"})

            local_modules = path / "node_modules"
            env_type = "In-Project (node_modules)" if local_modules.is_dir() else "Global (npm -g)"
            
            for dep in declared:
                pkg_dir = local_modules / dep["name"]
                dep_json = pkg_dir / "package.json"
                if dep_json.is_file():
                    try:
                        with open(dep_json, "r", encoding="utf-8", errors="ignore") as df:
                            d_data = json.load(df)
                        dep["installed_version"] = d_data.get("version", "installed")
                        dep["status"] = "MATCHED"
                    except Exception:
                        dep["installed_version"] = "unknown"
                        dep["status"] = "MATCHED"
                elif dep["name"] in self.global_node_pkgs:
                    dep["installed_version"] = self.global_node_pkgs[dep["name"]]
                    dep["status"] = "MATCHED"
                else:
                    dep["installed_version"] = None
                    dep["status"] = "MISSING"

            return {
                "name": data.get("name", path.name),
                "ecosystem": "Node.js",
                "path": str(path),
                "env_type": env_type,
                "declared_deps": declared
            }
        except Exception:
            return None

    def _parse_rust_project(self, path: Path) -> Optional[Dict[str, Any]]:
        cargo_toml = path / "Cargo.toml"
        target_dir = path / "target"
        return {
            "name": path.name,
            "ecosystem": "Rust",
            "path": str(path),
            "target_dir": str(target_dir) if target_dir.is_dir() else None,
            "target_size_mb": 0,
            "declared_deps": []
        }

    def _parse_flutter_project(self, path: Path) -> Optional[Dict[str, Any]]:
        pubspec = path / "pubspec.yaml"
        build_dir = path / "build"
        return {
            "name": path.name,
            "ecosystem": "Flutter",
            "path": str(path),
            "build_dir": str(build_dir) if build_dir.is_dir() else None,
            "build_size_mb": 0,
            "declared_deps": []
        }

    def _match_version(self, spec_str: str, inst_ver_str: str) -> str:
        if not spec_str:
            return "MATCHED"
        if HAS_PACKAGING:
            try:
                spec = SpecifierSet(spec_str)
                v = Version(inst_ver_str)
                return "MATCHED" if spec.contains(v) else "VERSION_DRIFT"
            except Exception:
                pass
        if spec_str.startswith("==") and spec_str[2:].strip() != inst_ver_str:
            return "VERSION_DRIFT"
        return "MATCHED"

    def get_transitive_closure(self, root_packages: Set[str]) -> Set[str]:
        closure = set()
        queue = list(root_packages)
        visited = set()

        while queue:
            curr = queue.pop(0)
            if curr in visited:
                continue
            visited.add(curr)
            norm_curr = normalize_name(curr)
            closure.add(norm_curr)

            reqs = self.global_python_requires.get(norm_curr, [])
            for r in reqs:
                norm_r = normalize_name(r)
                if norm_r not in visited:
                    queue.append(norm_r)
        return closure

    def classify_orphans(self) -> Dict[str, Any]:
        used_closure = self.get_transitive_closure(self.all_declared_python)
        all_installed = set(self.global_python_dists.keys())
        unreferenced = all_installed - used_closure

        tier1 = []
        tier2 = []
        tier3 = []

        for pkg in sorted(unreferenced):
            ver = self.global_python_dists.get(pkg, "")
            req_by = []
            for p, reqs in self.global_python_requires.items():
                if pkg in reqs:
                    req_by.append(p)

            item = {
                "name": pkg,
                "version": ver,
                "required_by": req_by
            }

            if pkg in CORE_PROTECTED_PACKAGES:
                tier1.append(item)
            elif pkg in CLI_OR_TOOL_PACKAGES:
                tier2.append(item)
            else:
                tier3.append(item)

        return {
            "total_installed": len(all_installed),
            "declared_count": len(self.all_declared_python),
            "active_or_transitive_count": len(used_closure),
            "unreferenced_count": len(unreferenced),
            "tier1_protected": tier1,
            "tier2_cli_tools": tier2,
            "tier3_pure_libraries": tier3
        }

    def scan_bloat(self) -> List[Dict[str, Any]]:
        bloat_list = []
        for p in self.projects:
            target_path_str = p.get("target_dir")
            if target_path_str:
                tp = Path(target_path_str)
                if tp.is_dir():
                    try:
                        sz = sum(f.stat().st_size for f in tp.rglob("*") if f.is_file())
                        sz_mb = round(sz / (1024 * 1024), 2)
                        if sz_mb > 0:
                            bloat_list.append({
                                "project": p["name"],
                                "path": str(tp),
                                "ecosystem": "Rust",
                                "type": "target/",
                                "size_mb": sz_mb,
                                "clean_cmd": f"cargo clean (in {p['path']})"
                            })
                    except Exception:
                        pass
            build_path_str = p.get("build_dir")
            if build_path_str:
                bp = Path(build_path_str)
                if bp.is_dir():
                    try:
                        sz = sum(f.stat().st_size for f in bp.rglob("*") if f.is_file())
                        sz_mb = round(sz / (1024 * 1024), 2)
                        if sz_mb > 0:
                            bloat_list.append({
                                "project": p["name"],
                                "path": str(bp),
                                "ecosystem": "Flutter",
                                "type": "build/",
                                "size_mb": sz_mb,
                                "clean_cmd": f"flutter clean (in {p['path']})"
                            })
                    except Exception:
                        pass
        return bloat_list

    def create_backup(self, backup_dir: Optional[Path] = None) -> Path:
        if backup_dir is None:
            backup_dir = self.root_dir / ".orphan_clean_backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = backup_dir / f"pip_backup_{timestamp}.txt"
        
        res = subprocess.run([sys.executable, "-m", "pip", "freeze"],
                             capture_output=True, text=True, check=True)
        with open(backup_file, "w", encoding="utf-8") as f:
            f.write("# orphan-clean Automatic Backup Snapshot\n")
            f.write(f"# Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# Root Scan Dir: {self.root_dir}\n\n")
            f.write(res.stdout)
            
        return backup_file

    def uninstall_packages(self, packages: List[str], backup: bool = True) -> Dict[str, Any]:
        filtered = []
        rejected = []
        for p in packages:
            norm = normalize_name(p)
            if norm in CORE_PROTECTED_PACKAGES:
                rejected.append(p)
            else:
                filtered.append(p)

        if not filtered:
            return {"success": False, "error": "No valid packages to uninstall.", "rejected": rejected}

        backup_path = None
        if backup:
            try:
                backup_path = str(self.create_backup())
            except Exception as e:
                return {"success": False, "error": f"Failed to create backup: {e}"}

        cmd = [sys.executable, "-m", "pip", "uninstall", "-y"] + filtered
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.load_global_environments()

        return {
            "success": res.returncode == 0,
            "uninstalled": filtered,
            "rejected": rejected,
            "backup_file": backup_path,
            "stdout": res.stdout,
            "stderr": res.stderr
        }

    def clean_bloat_target(self, target_path: str) -> Dict[str, Any]:
        p = Path(target_path).resolve()
        if not p.is_dir():
            return {"success": False, "error": "Directory does not exist"}
        if p.name not in ["target", "build", ".dart_tool"]:
            return {"success": False, "error": "Safety check failed: only target/ or build/ can be cleaned."}
        try:
            shutil.rmtree(p)
            return {"success": True, "cleaned_path": str(p)}
        except Exception as e:
            return {"success": False, "error": str(e)}
