#!/usr/bin/env python3
"""
Root entry point for Pith Autonomous Daily Publishing.
Usage:
  python3 run_daily.py                 # Live run using configured API keys
  python3 run_daily.py --dry-run       # Test run without calling external LLMs
  python3 run_daily.py --skip-audio    # Rebuild cards and feeds without generating audio
"""

import sys
from pipeline.orchestrate_daily import main

if __name__ == "__main__":
    main()
