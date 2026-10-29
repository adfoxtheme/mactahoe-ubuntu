"""Small file helpers for Whisker 2.8 rc files and the scoped GTK stylesheet."""
import argparse
from pathlib import Path
import re

IMPORT = '@import url("mactahoe-menu.css");'


def update_rc(text, settings):
    lines = text.splitlines()
    boundary = next((i for i, line in enumerate(lines) if line.strip().startswith("[")), len(lines))
    root, sections = lines[:boundary], lines[boundary:]
    keys = set(settings)
    root = [line for line in root if not ("=" in line and line.split("=", 1)[0].strip() in keys)]
    root.extend(f"{key}={value}" for key, value in settings.items())
    return "\n".join(root + sections) + "\n"


def add_import(text):
    # Reinstall should have exactly one import, before the user's other rules.
    return IMPORT + "\n" + "\n".join(line for line in text.splitlines() if line.strip() != IMPORT) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("rc", "css"))
    parser.add_argument("path", type=Path)
    parser.add_argument("settings", nargs="*")
    args = parser.parse_args()
    text = args.path.read_text(encoding="utf-8") if args.path.exists() else ""
    if args.action == "rc":
        settings = dict(item.split("=", 1) for item in args.settings)
        if not all(re.fullmatch(r"[a-z-]+", key) for key in settings):
            parser.error("Invalid rc setting name")
        result = update_rc(text, settings)
    else:
        result = add_import(text)
    args.path.parent.mkdir(parents=True, exist_ok=True)
    # Replace a symlink locally instead of editing its destination (possibly a system file).
    temporary = args.path.with_name(args.path.name + ".mactahoe-tmp")
    temporary.write_text(result, encoding="utf-8")
    temporary.replace(args.path)


if __name__ == "__main__":
    main()
