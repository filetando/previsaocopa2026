#!/usr/bin/env python3
"""
Hook PreToolUse: bloqueia escrita em data/raw/ fora de src/collection/
e bloqueia comandos destrutivos.
"""
import json
import sys


def main():
    hook_input = json.load(sys.stdin)
    tool_name = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input", {})

    if tool_name == "Write":
        file_path = tool_input.get("file_path", "")
        if "data/raw/" in file_path:
            print(json.dumps({
                "decision": "block",
                "reason": (
                    f"BLOQUEADO: data/raw/ e somente leitura. "
                    f"Escrita em '{file_path}' so e permitida em src/collection/. "
                    f"Use data/processed/ para dados derivados."
                )
            }))
            sys.exit(2)

    if tool_name == "Bash":
        command = tool_input.get("command", "")
        bloqueados = ["rm -rf", "git reset --hard", "git push --force", "DROP TABLE"]
        for cmd in bloqueados:
            if cmd in command:
                print(json.dumps({
                    "decision": "block",
                    "reason": f"BLOQUEADO: comando perigoso detectado: '{cmd}'"
                }))
                sys.exit(2)

    print(json.dumps({"decision": "allow"}))
    sys.exit(0)


if __name__ == "__main__":
    main()
