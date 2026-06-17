#!/usr/bin/env python3
"""
Hook PostToolUse: formata automaticamente arquivos Python apos escrita.
"""
import json
import subprocess
import sys


def main():
    hook_input = json.load(sys.stdin)
    tool_input = hook_input.get("tool_input", {})
    file_path = tool_input.get("file_path", "")

    if file_path.endswith(".py"):
        try:
            subprocess.run(["black", "--quiet", file_path], check=False)
            subprocess.run(["isort", "--quiet", file_path], check=False)
        except FileNotFoundError:
            pass

    sys.exit(0)


if __name__ == "__main__":
    main()
