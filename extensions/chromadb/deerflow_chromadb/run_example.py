#!/usr/bin/env python3
"""Wrapper to run the example with correct Python path."""

import sys
from pathlib import Path

# Add the extensions directory to Python path
extensions_dir = Path(__file__).parent
sys.path.insert(0, str(extensions_dir))

# Now we can import and run the example
from chromadb.example_usage import example_business_data

if __name__ == "__main__":
    example_business_data()
