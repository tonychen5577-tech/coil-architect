"""
Coil-Architect Pro - Main Entry Point
"""
import sys
from pathlib import Path

# Ensure root dir is in sys.path
root_dir = Path(__file__).resolve().parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from app import main

if __name__ == "__main__":
    main()
