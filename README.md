# Advanced Gmail Creator with Playwright

A sophisticated, enterprise-grade Gmail account creation tool built with Playwright, featuring advanced anti-detection measures, proxy management, and robust error handling.

![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![Playwright](https://img.shields.io/badge/playwright-1.41.0-green)
![License](https://img.shields.io/badge/license-MIT-blue)

## 🚀 Key Features

### Core Functionality
- **Bulk Account Creation**: Create multiple Gmail accounts efficiently with configurable batch sizes
- **Resume Capability**: Resume interrupted batches automatically
- **Advanced Stealth**: Browser fingerprint randomization and anti-detection measures
- **Proxy Support**: HTTP/HTTPS/SOCKS4/SOCKS5 proxies with health monitoring and rotation
- **User Profile Generation**: Realistic profiles with diverse demographics and locales

### Anti-Detection & Security
- **Playwright Stealth**: Advanced stealth plugin integration
- **Fingerprint Randomization**: Random user agents, screen resolutions, timezones
- **Human-like Behavior**: Random delays, mouse movements, and typing patterns
- **WebDriver Detection Bypass**: Override navigator.webdriver and related properties

### Data Management
- **SQLite Database**: Persistent storage for accounts and batch information
- **Multiple Export Formats**: JSON, CSV, and TXT export options
- **Account Status Tracking**: Monitor creation, verification, and account health
- **Comprehensive Logging**: Rotating logs with multiple levels and colored output

## 📋 Requirements

- Python 3.8 or higher
- At least 2GB RAM
- Stable internet connection
- Optional: Premium proxy service for better success rates

## 🛠️ Installation

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/playwright-gmail-creator.git
cd playwright-gmail-creator
```

### 2. Create Virtual Environment
```bash
python -m venv venv

# On Linux/macOS:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

### 4. Verify Installation
```bash
python main.py validate
```

## ⚙️ Configuration

### Quick Start Configuration
The application will create a default configuration file on first run. For immediate use:

```bash
# Create default config
python main.py validate

# Edit config/config.yaml with your preferences
```

### Detailed Configuration

#### Basic Configuration (`config/minimal_config.yaml`)
```yaml
account:
  batch_size: 3
  delay_between_accounts: [5, 15]
browser:
  headless: false
logging:
  level: "INFO"
```

#### Advanced Configuration (`config/advanced_config.yaml`)
```yaml
proxy:
  enabled: true
  auto_fetch_free: true
  rotation_method: "best"
  preferred_countries: ["US", "UK", "CA"]

browser:
  browser_type: "chromium"
  headless: true
  viewport_width: 1920
  viewport_height: 1080

account:
  batch_size: 10
  delay_between_accounts: [20, 60]
  max_retries: 5
  output_format: "json"

stealth:
  randomize_fingerprints: true
  randomize_user_agents: true
  stealth_plugin_enabled: true

logging:
  level: "DEBUG"
  file_enabled: true
  console_enabled: true
```

### Configuration Options

#### Proxy Settings
```yaml
proxy:
  enabled: true                    # Enable/disable proxy usage
  auto_fetch_free: false          # Automatically fetch free proxies
  proxy_file: "proxies.json"      # Load proxies from file
  proxy_list: []                  # Direct proxy list
  rotation_method: "random"       # "random", "sequential", "best"
  health_check_interval: 300      # Health check interval (seconds)
  max_failures: 3                 # Max failures before proxy is disabled
  timeout: 10                     # Proxy timeout (seconds)
  preferred_countries: ["US"]     # Prefer proxies from these countries
```

#### Browser Settings
```yaml
browser:
  browser_type: "chromium"        # "chromium", "firefox", "webkit"
  headless: false                 # Run in headless mode
  viewport_width: 1920            # Browser viewport width
  viewport_height: 1080           # Browser viewport height
  timezone_id: null               # Override timezone
  locale: "en-US"                 # Browser locale
  user_data_dir: null             # Custom user data directory
```

#### Account Creation Settings
```yaml
account:
  batch_size: 5                   # Accounts per batch
  delay_between_accounts: [10, 30] # Delay range (seconds)
  delay_between_actions: [1, 3]   # Action delay range (seconds)
  max_retries: 3                  # Retry attempts per account
  retry_delay: 60                 # Delay between retries (seconds)
  save_to_file: true              # Auto-save accounts
  output_format: "json"           # "json", "csv", "txt"
  verify_accounts: false          # Enable account verification
```

#### Stealth & Anti-Detection
```yaml
stealth:
  randomize_fingerprints: true    # Randomize browser fingerprints
  randomize_user_agents: true     # Use random user agents
  randomize_screen_resolution: true # Random screen resolutions
  randomize_timezone: true        # Random timezones
  randomize_language: true        # Random languages
  stealth_plugin_enabled: true    # Enable stealth plugin
  navigator_webdriver_override: true # Override webdriver detection
```

## 🚀 Usage

### Command Line Interface

#### Create Gmail Accounts
```bash
# Create 5 accounts with default settings
python main.py create 5

# Create 10 accounts with resume capability
python main.py create 10 --resume

# Create accounts and save results to file
python main.py create 3 --output results.json

# Use custom configuration
python main.py --config config/advanced_config.yaml create 5
```

#### Test Proxy Connectivity
```bash
# Test all configured proxies
python main.py test-proxies
```

#### View Statistics
```bash
# Show account and system statistics
python main.py stats
```

#### Export Accounts
```bash
# Export all accounts to JSON
python main.py export accounts.json json

# Export only created accounts to CSV
python main.py export created_accounts.csv csv --status created

# Export credentials to text file
python main.py export credentials.txt txt --status created
```

#### Validate Configuration
```bash
# Validate current configuration
python main.py validate
```

### Programmatic Usage

```python
import asyncio
from src.config_manager import ConfigManager
from src.gmail_creator import GmailCreator

async def create_accounts():
    # Initialize
    config_manager = ConfigManager("config/my_config.yaml")
    config_manager.setup_logging()
    
    # Create Gmail creator
    creator = GmailCreator(config_manager)
    await creator.initialize()
    
    # Create 3 accounts
    results = await creator.create_bulk_accounts(3)
    
    # Process results
    for result in results:
        if result.get('status') == 'created':
            print(f"✅ Created: {result['email']}")
        else:
            print(f"❌ Failed: {result.get('error', 'Unknown error')}")

# Run
asyncio.run(create_accounts())
```

## 🔧 Advanced Features

### Proxy Management

#### Using Your Own Proxies
```yaml
# In config.yaml
proxy:
  enabled: true
  proxy_list:
    - "proxy1.example.com:8080"
    - "proxy2.example.com:3128:username:password"
    - "socks5://proxy3.example.com:1080"
```

#### Proxy File Format (`proxies.json`)
```json
[
  {
    "host": "proxy1.example.com",
    "port": 8080,
    "type": "http",
    "username": null,
    "password": null,
    "country": "US",
    "city": "New York"
  }
]
```

### Custom User Profiles

Create custom name databases:
```python
from src.user_profile_generator import UserProfileGenerator

generator = UserProfileGenerator(config_manager)

# Generate profiles with specific locales
config.user_profile.supported_locales = ["es_ES", "fr_FR"]
profile = generator.generate_profile()
```

### Batch Processing with Resume

The application automatically saves batch state and can resume interrupted operations:

```bash
# Start batch creation
python main.py create 100

# If interrupted, resume with:
python main.py create 100 --resume
```

### Account Management

```python
from src.account_manager import AccountManager, AccountStatus

manager = AccountManager(config_manager)

# Get statistics
stats = manager.get_statistics()
print(f"Success rate: {stats['success_rate']:.1f}%")

# Export specific account types
manager.export_accounts(
    "verified_accounts.json", 
    "json", 
    AccountStatus.VERIFIED
)
```

## 📊 Monitoring & Logging

### Log Files
- `logs/gmail_creator.log` - Main application log
- `logs/gmail_creator.log.1` - Rotated log files
- `output/creation_report_*.json` - Batch creation reports

### Log Levels
- `DEBUG` - Detailed debugging information
- `INFO` - General information about progress
- `WARNING` - Warning messages and recoverable errors
- `ERROR` - Error messages requiring attention
- `CRITICAL` - Critical errors that stop execution

### Monitoring Progress
```bash
# Follow log file in real-time
tail -f logs/gmail_creator.log

# Watch statistics
watch -n 5 'python main.py stats'
```

## 🛡️ Best Practices

### For Higher Success Rates
1. **Use Quality Proxies**: Premium residential proxies work best
2. **Reasonable Delays**: Don't set delays too low (minimum 10 seconds between accounts)
3. **Batch Sizes**: Keep batches small (3-10 accounts) to avoid detection
4. **Rotate Everything**: Enable all randomization options
5. **Monitor Logs**: Watch for patterns in failures

### Security Considerations
1. **Secure Storage**: Store account credentials securely
2. **Proxy Security**: Use trusted proxy providers
3. **Rate Limiting**: Respect service limits to avoid IP bans
4. **Legal Compliance**: Ensure compliance with terms of service

### Performance Optimization
1. **Resource Management**: Monitor memory usage with large batches
2. **Network Stability**: Use stable internet connection
3. **Concurrent Limits**: Adjust batch size based on system capabilities
4. **Database Maintenance**: Regular cleanup of old batch logs

## 📈 Troubleshooting

### Common Issues

#### "No active proxies available"
```bash
# Test proxy connectivity
python main.py test-proxies

# Check proxy configuration
python main.py validate
```

#### "Phone verification required"
```yaml
# In config.yaml - this is expected for some accounts
account:
  phone_verification: true  # Enable if you have phone numbers
```

#### "Account creation timeout"
```yaml
# Increase timeouts in config
browser:
  additional_args:
    - "--timeout=30000"
```

#### High failure rate
1. Check proxy quality and rotation
2. Increase delays between actions
3. Enable all stealth features
4. Monitor for IP-based blocking

### Debug Mode
```bash
# Enable verbose logging
python main.py --verbose create 3

# Check configuration
python main.py --verbose validate
```

### Performance Issues
```bash
# Run with fewer concurrent operations
# Modify config.yaml:
account:
  batch_size: 1  # Create one at a time
  delay_between_accounts: [30, 60]  # Longer delays
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Setup
```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
pytest tests/

# Code formatting
black src/
flake8 src/
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

This tool is for educational and legitimate purposes only. Users are responsible for:
- Complying with Google's Terms of Service
- Following applicable laws and regulations
- Using accounts responsibly and ethically
- Respecting rate limits and service guidelines

The developers are not responsible for any misuse of this software.

## 🙏 Acknowledgments

- [Playwright](https://playwright.dev/) - Modern web automation
- [playwright-stealth](https://github.com/AtuboDad/playwright_stealth) - Stealth plugin
- [FreeProxy](https://github.com/jundymek/free-proxy) - Free proxy fetching
- [Faker](https://faker.readthedocs.io/) - Realistic fake data generation

## 📞 Support

- 📧 Email: support@example.com
- 🐛 Issues: [GitHub Issues](https://github.com/yourusername/playwright-gmail-creator/issues)
- 💬 Discussions: [GitHub Discussions](https://github.com/yourusername/playwright-gmail-creator/discussions)

---

**Made with ❤️ for automation enthusiasts**