#!/usr/bin/env python3
"""
Quick test script to check what packages are available and working
"""

import sys
print(f"Python version: {sys.version}")

# Test essential imports
try:
    import sqlite3
    print("✅ sqlite3 - OK")
except ImportError as e:
    print(f"❌ sqlite3 - {e}")

try:
    import json
    print("✅ json - OK")
except ImportError as e:
    print(f"❌ json - {e}")

try:
    import asyncio
    print("✅ asyncio - OK")
except ImportError as e:
    print(f"❌ asyncio - {e}")

# Test external packages
packages_to_test = [
    'playwright',
    'requests', 
    'aiohttp',
    'fake_useragent',
    'unidecode',
    'colorlog',
    'rich',
    'yaml',
    'user_agents'
]

for package in packages_to_test:
    try:
        __import__(package)
        print(f"✅ {package} - OK")
    except ImportError as e:
        print(f"❌ {package} - Not installed")

print("\n" + "="*50)
print("Basic functionality test:")

try:
    # Test basic functionality
    from pathlib import Path
    from datetime import datetime
    from dataclasses import dataclass
    from enum import Enum
    
    @dataclass 
    class TestClass:
        name: str
        value: int
    
    test = TestClass("test", 42)
    print("✅ Dataclasses work")
    
    # Test async
    async def test_async():
        return "async works"
    
    result = asyncio.run(test_async())
    print("✅ Asyncio works")
    
    print("✅ Core Python functionality is working!")
    
except Exception as e:
    print(f"❌ Core functionality test failed: {e}")