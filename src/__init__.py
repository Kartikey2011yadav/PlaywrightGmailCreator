"""
Advanced Gmail Creator with Playwright

A sophisticated Gmail account creation tool with advanced anti-detection,
proxy management, and comprehensive monitoring capabilities.
"""

__version__ = "1.0.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

from .config_manager import ConfigManager
from .gmail_creator import GmailCreator
from .account_manager import AccountManager
from .user_profile_generator import UserProfileGenerator
from .proxy_manager import ProxyManager
from .stealth_manager import StealthManager

__all__ = [
    "ConfigManager",
    "GmailCreator", 
    "AccountManager",
    "UserProfileGenerator",
    "ProxyManager",
    "StealthManager"
]