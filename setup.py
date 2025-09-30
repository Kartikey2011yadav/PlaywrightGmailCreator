#!/usr/bin/env python3
"""
Setup script for Gmail Creator

This script helps set up the environment and verify the installation.
"""

import os
import sys
import subprocess
import platform
from pathlib import Path


def print_banner():
    """Print setup banner"""
    print("""
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║     Advanced Gmail Creator with Playwright Setup         ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
    """)


def check_python_version():
    """Check if Python version is compatible"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Error: Python 3.8 or higher is required")
        print(f"   Current version: {version.major}.{version.minor}.{version.micro}")
        return False
    
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} - Compatible")
    return True


def check_pip():
    """Check if pip is available"""
    try:
        import pip
        print("✅ pip is available")
        return True
    except ImportError:
        print("❌ Error: pip is not available")
        return False


def install_requirements():
    """Install required packages"""
    print("\n📦 Installing requirements...")
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
        ])
        print("✅ Requirements installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing requirements: {e}")
        return False


def install_playwright_browsers():
    """Install Playwright browsers"""
    print("\n🌐 Installing Playwright browsers...")
    try:
        subprocess.check_call([
            sys.executable, "-m", "playwright", "install", "chromium"
        ])
        print("✅ Playwright browsers installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing Playwright browsers: {e}")
        return False


def create_directories():
    """Create necessary directories"""
    print("\n📁 Creating directories...")
    directories = ["logs", "output", "data", "config"]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"   Created: {directory}/")
    
    print("✅ Directories created successfully")


def verify_installation():
    """Verify the installation"""
    print("\n🔍 Verifying installation...")
    
    try:
        # Test imports
        import playwright
        import asyncio
        import aiohttp
        print("✅ Core dependencies imported successfully")
        
        # Test configuration
        subprocess.check_call([sys.executable, "main.py", "validate"])
        print("✅ Configuration validation successful")
        
        return True
        
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False


def show_next_steps():
    """Show next steps to the user"""
    print("""
╔═══════════════════════════════════════════════════════════╗
║                        Setup Complete!                    ║
╚═══════════════════════════════════════════════════════════╝

🎉 Installation completed successfully!

📋 Next Steps:

1. Configure the application:
   Edit config/config.yaml with your settings

2. Test proxy connectivity (if using proxies):
   python main.py test-proxies

3. Create your first Gmail accounts:
   python main.py create 3

4. View account statistics:
   python main.py stats

📚 Documentation:
   - Full documentation: README.md
   - Configuration examples: config/ directory
   - Logs will be saved to: logs/ directory
   - Accounts will be saved to: output/ directory

⚠️  Important Notes:
   - Use responsibly and comply with terms of service
   - Test with small batches first (1-3 accounts)
   - Monitor logs for any issues
   - Use quality proxies for better success rates

🚀 Happy account creating!
    """)


def main():
    """Main setup function"""
    print_banner()
    
    # Check system requirements
    if not check_python_version():
        sys.exit(1)
    
    if not check_pip():
        sys.exit(1)
    
    # Install dependencies
    if not install_requirements():
        sys.exit(1)
    
    if not install_playwright_browsers():
        sys.exit(1)
    
    # Setup directories
    create_directories()
    
    # Verify installation
    if not verify_installation():
        print("\n⚠️  Installation completed but verification failed.")
        print("   You may still be able to use the application.")
    
    # Show next steps
    show_next_steps()


if __name__ == "__main__":
    main()