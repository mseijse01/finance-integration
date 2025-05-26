#!/usr/bin/env python3
"""
Utility to download and set up NLTK resources.
Handles SSL certificate issues that commonly occur on macOS.
"""

import ssl
import sys

import nltk


def setup_nltk():
    print("Setting up NLTK resources...")

    # Fix SSL certificate issues
    try:
        _create_unverified_https_context = ssl._create_unverified_context
    except AttributeError:
        pass
    else:
        ssl._create_default_https_context = _create_unverified_https_context

    # Download required NLTK datasets
    try:
        print("Downloading vader_lexicon...")
        nltk.download("vader_lexicon", quiet=False)
        print("NLTK setup complete!")
        return True
    except Exception as e:
        print(f"Error setting up NLTK: {e}", file=sys.stderr)
        return False


if __name__ == "__main__":
    success = setup_nltk()
    sys.exit(0 if success else 1)
