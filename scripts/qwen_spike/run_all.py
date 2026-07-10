"""Run the non-destructive Qwen spike scripts in sequence."""

import subprocess
import sys
from pathlib import Path

SCRIPTS = [
    "01_basic_call.py",
    "02_structured_output.py",
    "03_single_tool_call.py",
    "04_tool_roundtrip.py",
    "05_error_handling.py",
]


def main() -> None:
    directory = Path(__file__).resolve().parent
    for script in SCRIPTS:
        print(f"\n>>> Running {script}")
        subprocess.run([sys.executable, str(directory / script)], check=True)


if __name__ == "__main__":
    main()
