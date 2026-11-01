#!/usr/bin/env python3
"""Read-only executable inventory; never launches an engine or checks a license."""
import json
import os
from pathlib import Path
import platform
import shutil
import sys


def executable(path):
    return path.is_file() and os.access(path, os.X_OK)


def unique_executables(paths):
    found = []
    seen = set()
    for path in paths:
        if executable(path):
            resolved = str(path.resolve())
            if resolved not in seen:
                seen.add(resolved)
                found.append(resolved)
    return found


def probe():
    names = {"Stata": ["stata-mp", "stata-se", "stata", "StataMP", "StataSE", "Stata"],
             "SPSS": ["stats", "statisticsb", "spss"],
             "R": ["Rscript", "R"], "Python": ["python3", "python"]}
    candidates = {key: [Path(path) for name in values if (path := shutil.which(name))]
                  for key, values in names.items()}
    candidates["Python"].insert(0, Path(sys.executable))
    if platform.system() == "Darwin":
        for edition in ("StataMP", "StataSE", "Stata"):
            candidates["Stata"].append(Path(f"/Applications/Stata/{edition}.app/Contents/MacOS/{edition}"))
            candidates["Stata"].append(Path(f"/Applications/{edition}.app/Contents/MacOS/{edition}"))
        applications = Path("/Applications")
        if applications.is_dir():
            for root in applications.glob("IBM SPSS Statistics*"):
                for app in (root, root / "SPSS Statistics.app", root / "IBM SPSS Statistics.app"):
                    for name in ("stats", "statisticsb"):
                        candidates["SPSS"].append(app / "Contents" / "MacOS" / name)
        candidates["R"].extend([Path("/Library/Frameworks/R.framework/Resources/bin/Rscript"),
                                 Path("/Library/Frameworks/R.framework/Resources/bin/R")])
    engines = {}
    for name, paths in candidates.items():
        paths_found = unique_executables(paths)
        engines[name] = {"state": "executable_found" if paths_found else "not_found",
                         "executables": paths_found, "version": None,
                         "license_checked": False, "launch_tested": False}
    return {"schema_version": 1, "platform": platform.system(), "engines": engines,
            "limitations": ["Executable presence does not confirm product identity, version, license, required modules, or batch capability.",
                            "not_found means not found in PATH and the limited locations checked; it does not prove absence.",
                            "No engine was executed. Confirm executable identity, exact version and authorized license before using native output."]}


if __name__ == "__main__":
    print(json.dumps(probe(), ensure_ascii=False, indent=2))
