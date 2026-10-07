"""Build on the target OS: Windows EXE cannot be produced by a Linux build."""
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
subprocess.run([sys.executable, "-m", "PyInstaller", "--clean", "--noconfirm", "--onefile",
                "--name", "Auto-DD", "--collect-all", "auto_dd", "--collect-all", "psycopg",
                "--collect-all", "psycopg_binary", "--collect-submodules", "google.cloud.bigquery",
                "--collect-submodules", "google.auth", str(root / "desktop.py")], cwd=root, check=True)
