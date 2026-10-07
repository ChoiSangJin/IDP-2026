"""PyInstaller entry point; launching without arguments opens the local UI."""
from auto_dd.cli import main
raise SystemExit(main())
