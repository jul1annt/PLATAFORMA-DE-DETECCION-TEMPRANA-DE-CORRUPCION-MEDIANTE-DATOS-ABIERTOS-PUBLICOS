"""Trusted entrypoint for -I subprocesses; no inherited Python path or site hooks."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from analytics_ml.cli import main

if __name__ == '__main__':
    main()
