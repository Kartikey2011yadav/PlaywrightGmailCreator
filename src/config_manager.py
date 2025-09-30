"""
Configuration Management System for Gmail Creator

This module handles all configuration settings, logging setup,
and environment management.
"""

import json
import logging
import logging.handlers
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict, field
from enum import Enum

# Optional imports
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
    yaml = None

try:
    import colorlog
    COLORLOG_AVAILABLE = True
except ImportError:
    COLORLOG_AVAILABLE = False
    colorlog = None

try:
    from rich.logging import RichHandler
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    RichHandler = None


class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class BrowserType(Enum):
    CHROMIUM = "chromium"
    FIREFOX = "firefox"
    WEBKIT = "webkit"


@dataclass
class ProxyConfig:
    """Proxy configuration settings"""
    enabled: bool = True
    auto_fetch_free: bool = False
    proxy_file: Optional[str] = None
    proxy_list: List[str] = field(default_factory=list)
    rotation_method: str = "random"  # random, sequential, best
    health_check_interval: int = 300
    max_failures: int = 3
    timeout: int = 10
    preferred_countries: List[str] = field(default_factory=list)


@dataclass
class BrowserConfig:
    """Browser configuration settings"""
    browser_type: BrowserType = BrowserType.CHROMIUM
    headless: bool = False
    user_data_dir: Optional[str] = None
    viewport_width: int = 1920
    viewport_height: int = 1080
    timezone_id: Optional[str] = None
    locale: str = "en-US"
    permissions: List[str] = field(default_factory=list)
    geolocation: Optional[Dict[str, float]] = None
    device_scale_factor: float = 1.0
    is_mobile: bool = False
    has_touch: bool = False
    
    # Anti-detection settings
    disable_web_security: bool = True
    disable_features: List[str] = field(default_factory=lambda: [
        "VizDisplayCompositor",
        "TranslateUI",
        "BlinkGenPropertyTrees"
    ])
    additional_args: List[str] = field(default_factory=lambda: [
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-blink-features=AutomationControlled",
        "--disable-dev-shm-usage",
        "--no-sandbox"
    ])


@dataclass
class UserProfileConfig:
    """User profile generation settings"""
    use_real_names: bool = True
    name_database_file: Optional[str] = None
    supported_locales: List[str] = field(default_factory=lambda: [
        "en_US", "en_GB", "es_ES", "fr_FR", "de_DE", "it_IT"
    ])
    age_range: tuple = (18, 65)
    password_length: int = 16
    use_complex_passwords: bool = True
    birth_year_range: tuple = (1960, 2005)


@dataclass
class AccountConfig:
    """Account creation settings"""
    batch_size: int = 5
    delay_between_accounts: tuple = (10, 30)  # min, max seconds
    delay_between_actions: tuple = (1, 3)  # min, max seconds
    max_retries: int = 3
    retry_delay: int = 60
    save_to_file: bool = True
    output_format: str = "json"  # json, csv, txt
    verify_accounts: bool = False
    phone_verification: bool = False
    recovery_email: bool = False


@dataclass
class StealthConfig:
    """Stealth and anti-detection settings"""
    randomize_fingerprints: bool = True
    randomize_user_agents: bool = True
    randomize_screen_resolution: bool = True
    randomize_timezone: bool = True
    randomize_language: bool = True
    stealth_plugin_enabled: bool = True
    navigator_webdriver_override: bool = True
    chrome_runtime_override: bool = True
    permissions_override: bool = True
    plugins_override: bool = True


@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: LogLevel = LogLevel.INFO
    console_enabled: bool = True
    file_enabled: bool = True
    file_path: str = "logs/gmail_creator.log"
    max_file_size: int = 10  # MB
    backup_count: int = 5
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format: str = "%Y-%m-%d %H:%M:%S"
    colored_console: bool = True
    rich_console: bool = True


@dataclass
class GmailCreatorConfig:
    """Main configuration class"""
    proxy: ProxyConfig = field(default_factory=ProxyConfig)
    browser: BrowserConfig = field(default_factory=BrowserConfig)
    user_profile: UserProfileConfig = field(default_factory=UserProfileConfig)
    account: AccountConfig = field(default_factory=AccountConfig)
    stealth: StealthConfig = field(default_factory=StealthConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    
    # Paths
    project_root: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir: str = "output"
    logs_dir: str = "logs"
    data_dir: str = "data"
    config_dir: str = "config"


class ConfigManager:
    """Configuration manager for loading, saving, and validating settings"""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file or "config/config.yaml"
        self.config = GmailCreatorConfig()
        self.logger = None
        
    def load_config(self, config_file: Optional[str] = None) -> GmailCreatorConfig:
        """Load configuration from file"""
        config_path = config_file or self.config_file
        
        if not os.path.exists(config_path):
            self.save_config(config_path)
            return self.config
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                if config_path.endswith('.json'):
                    data = json.load(f)
                else:  # YAML
                    if YAML_AVAILABLE:
                        data = yaml.safe_load(f) or {}
                    else:
                        raise ImportError("YAML support not available - please install pyyaml or use JSON config")
            
            # Update config with loaded data
            self._update_config_from_dict(data)
            
            if self.logger:
                self.logger.info(f"Configuration loaded from {config_path}")
                
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to load config from {config_path}: {e}")
            # Use default config
            
        return self.config
    
    def save_config(self, config_file: Optional[str] = None) -> None:
        """Save current configuration to file"""
        config_path = config_file or self.config_file
        
        # Ensure config directory exists
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        try:
            config_dict = asdict(self.config)
            
            with open(config_path, 'w', encoding='utf-8') as f:
                if config_path.endswith('.json'):
                    json.dump(config_dict, f, indent=2, default=str)
                else:  # YAML
                    if YAML_AVAILABLE:
                        yaml.dump(config_dict, f, default_flow_style=False, indent=2)
                    else:
                        # Fallback to JSON if YAML not available
                        json.dump(config_dict, f, indent=2, default=str)
            
            if self.logger:
                self.logger.info(f"Configuration saved to {config_path}")
                
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to save config to {config_path}: {e}")
    
    def _update_config_from_dict(self, data: Dict[str, Any]) -> None:
        """Update configuration from dictionary"""
        def update_dataclass(obj, updates):
            for key, value in updates.items():
                if hasattr(obj, key):
                    attr = getattr(obj, key)
                    # Check if this is a nested dataclass by checking the field annotation
                    if hasattr(obj, '__dataclass_fields__') and key in obj.__dataclass_fields__:
                        field = obj.__dataclass_fields__[key]
                        if hasattr(field.type, '__dataclass_fields__'):
                            # Nested dataclass
                            if isinstance(value, dict):
                                update_dataclass(attr, value)
                        else:
                            # Simple attribute
                            if key in ['browser_type'] and isinstance(value, str):
                                # Handle enum conversion
                                try:
                                    setattr(obj, key, BrowserType(value))
                                except ValueError:
                                    continue
                            elif key in ['level'] and isinstance(value, str):
                                try:
                                    setattr(obj, key, LogLevel(value))
                                except ValueError:
                                    continue
                            else:
                                setattr(obj, key, value)
                    elif hasattr(attr, '__dict__'):
                        # Object with dict
                        for sub_key, sub_value in value.items():
                            if hasattr(attr, sub_key):
                                setattr(attr, sub_key, sub_value)
                    else:
                        # Simple attribute - fallback
                        setattr(obj, key, value)
        
        update_dataclass(self.config, data)
    
    def setup_logging(self) -> logging.Logger:
        """Setup logging based on configuration"""
        # Create logs directory
        logs_dir = os.path.join(self.config.project_root, self.config.logs_dir)
        os.makedirs(logs_dir, exist_ok=True)
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, self.config.logging.level.value))
        
        # Clear existing handlers
        root_logger.handlers.clear()
        
        # Create formatters
        if self.config.logging.colored_console and COLORLOG_AVAILABLE:
            console_formatter = colorlog.ColoredFormatter(
                '%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt=self.config.logging.date_format,
                log_colors={
                    'DEBUG': 'cyan',
                    'INFO': 'green',
                    'WARNING': 'yellow',
                    'ERROR': 'red',
                    'CRITICAL': 'red,bg_white',
                }
            )
        else:
            console_formatter = logging.Formatter(
                self.config.logging.format,
                datefmt=self.config.logging.date_format
            )
        
        file_formatter = logging.Formatter(
            self.config.logging.format,
            datefmt=self.config.logging.date_format
        )
        
        # Console handler
        if self.config.logging.console_enabled:
            if self.config.logging.rich_console and RICH_AVAILABLE:
                from rich.logging import RichHandler
                console_handler = RichHandler(rich_tracebacks=True)
                console_handler.setFormatter(logging.Formatter("%(message)s"))
            else:
                console_handler = logging.StreamHandler()
                console_handler.setFormatter(console_formatter)
            
            console_handler.setLevel(getattr(logging, self.config.logging.level.value))
            root_logger.addHandler(console_handler)
        
        # File handler
        if self.config.logging.file_enabled:
            log_file = os.path.join(logs_dir, os.path.basename(self.config.logging.file_path))
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=self.config.logging.max_file_size * 1024 * 1024,
                backupCount=self.config.logging.backup_count,
                encoding='utf-8'
            )
            file_handler.setFormatter(file_formatter)
            file_handler.setLevel(getattr(logging, self.config.logging.level.value))
            root_logger.addHandler(file_handler)
        
        # Create main logger
        self.logger = logging.getLogger('gmail_creator')
        self.logger.info("Logging system initialized")
        
        return self.logger
    
    def create_directories(self) -> None:
        """Create necessary project directories"""
        directories = [
            self.config.output_dir,
            self.config.logs_dir,
            self.config.data_dir,
            self.config.config_dir
        ]
        
        for directory in directories:
            dir_path = os.path.join(self.config.project_root, directory)
            os.makedirs(dir_path, exist_ok=True)
            
        if self.logger:
            self.logger.info("Project directories created/verified")
    
    def validate_config(self) -> List[str]:
        """Validate configuration and return list of errors"""
        errors = []
        
        # Validate proxy settings
        if self.config.proxy.enabled:
            if not self.config.proxy.auto_fetch_free and not self.config.proxy.proxy_file and not self.config.proxy.proxy_list:
                errors.append("Proxy enabled but no proxy source configured")
        
        # Validate paths
        if self.config.user_profile.name_database_file:
            if not os.path.exists(self.config.user_profile.name_database_file):
                errors.append(f"Name database file not found: {self.config.user_profile.name_database_file}")
        
        # Validate batch size
        if self.config.account.batch_size <= 0:
            errors.append("Batch size must be greater than 0")
        
        # Validate age range
        if self.config.user_profile.age_range[0] >= self.config.user_profile.age_range[1]:
            errors.append("Invalid age range")
        
        return errors
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Get a summary of current configuration"""
        return {
            "proxy_enabled": self.config.proxy.enabled,
            "browser_type": self.config.browser.browser_type.value,
            "headless_mode": self.config.browser.headless,
            "batch_size": self.config.account.batch_size,
            "stealth_enabled": self.config.stealth.stealth_plugin_enabled,
            "logging_level": self.config.logging.level.value,
            "output_format": self.config.account.output_format
        }


# Example configuration files
def create_example_configs():
    """Create example configuration files"""
    
    # Create minimal config
    minimal_config = {
        "account": {
            "batch_size": 3,
            "delay_between_accounts": [5, 15]
        },
        "browser": {
            "headless": False
        },
        "logging": {
            "level": "INFO"
        }
    }
    
    # Create advanced config
    advanced_config = {
        "proxy": {
            "enabled": True,
            "auto_fetch_free": True,
            "rotation_method": "best",
            "preferred_countries": ["US", "UK", "CA"]
        },
        "browser": {
            "browser_type": "chromium",
            "headless": True,
            "viewport_width": 1920,
            "viewport_height": 1080
        },
        "account": {
            "batch_size": 10,
            "delay_between_accounts": [20, 60],
            "max_retries": 5,
            "output_format": "json"
        },
        "stealth": {
            "randomize_fingerprints": True,
            "randomize_user_agents": True,
            "stealth_plugin_enabled": True
        },
        "logging": {
            "level": "DEBUG",
            "file_enabled": True,
            "console_enabled": True
        }
    }
    
    return minimal_config, advanced_config


if __name__ == "__main__":
    # Example usage
    config_manager = ConfigManager()
    logger = config_manager.setup_logging()
    config_manager.create_directories()
    
    # Validate configuration
    errors = config_manager.validate_config()
    if errors:
        logger.error(f"Configuration validation errors: {errors}")
    else:
        logger.info("Configuration is valid")
    
    # Save example configs
    minimal, advanced = create_example_configs()
    
    os.makedirs("config", exist_ok=True)
    with open("config/minimal_config.yaml", "w") as f:
        yaml.dump(minimal, f, indent=2)
    
    with open("config/advanced_config.yaml", "w") as f:
        yaml.dump(advanced, f, indent=2)
    
    logger.info("Example configuration files created")