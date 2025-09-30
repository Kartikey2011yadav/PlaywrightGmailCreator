"""
Stealth and Anti-Detection Manager

This module provides advanced stealth features, browser fingerprint randomization,
and anti-detection measures for Gmail account creation.
"""

import random
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
import asyncio

# Optional user_agents import
try:
    from user_agents import parse as parse_user_agent
    USER_AGENTS_AVAILABLE = True
except ImportError:
    USER_AGENTS_AVAILABLE = False
    def parse_user_agent(ua_string):
        """Dummy function when user_agents is not available"""
        class DummyUA:
            class OS:
                family = "Windows"
        class DummyResult:
            os = DummyUA.OS()
        return DummyResult()

from .config_manager import ConfigManager, GmailCreatorConfig

logger = logging.getLogger(__name__)


class StealthManager:
    """Manages stealth and anti-detection features"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager.config
        
        # User agents database
        self.user_agents = [
            # Chrome on Windows
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
            
            # Chrome on macOS
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            
            # Chrome on Linux
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            
            # Firefox on Windows
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:119.0) Gecko/20100101 Firefox/119.0",
            
            # Firefox on macOS
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:119.0) Gecko/20100101 Firefox/119.0",
            
            # Safari on macOS
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
            
            # Edge
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
        ]
        
        # Screen resolutions
        self.screen_resolutions = [
            (1920, 1080), (1366, 768), (1536, 864), (1440, 900),
            (1280, 720), (1280, 800), (1600, 900), (1024, 768),
            (1680, 1050), (1920, 1200), (2560, 1440), (3840, 2160)
        ]
        
        # Timezones
        self.timezones = [
            "America/New_York", "America/Los_Angeles", "America/Chicago",
            "Europe/London", "Europe/Paris", "Europe/Berlin", "Europe/Rome",
            "Asia/Tokyo", "Asia/Shanghai", "Asia/Kolkata", "Australia/Sydney"
        ]
        
        # Languages
        self.languages = [
            "en-US,en;q=0.9", "en-GB,en;q=0.9", "es-ES,es;q=0.9",
            "fr-FR,fr;q=0.9", "de-DE,de;q=0.9", "it-IT,it;q=0.9",
            "pt-BR,pt;q=0.9", "ru-RU,ru;q=0.9", "ja-JP,ja;q=0.9"
        ]
        
        # Platform data
        self.platforms = {
            "Windows": {
                "platform": "Win32",
                "oscpu": "Windows NT 10.0; Win64; x64",
                "userAgent_pattern": "Windows NT 10.0; Win64; x64"
            },
            "macOS": {
                "platform": "MacIntel", 
                "oscpu": "Intel Mac OS X 10.15.7",
                "userAgent_pattern": "Macintosh; Intel Mac OS X 10_15_7"
            },
            "Linux": {
                "platform": "Linux x86_64",
                "oscpu": "Linux x86_64", 
                "userAgent_pattern": "X11; Linux x86_64"
            }
        }
    
    def get_random_user_agent(self) -> str:
        """Get a random user agent"""
        if self.config.stealth.randomize_user_agents:
            return random.choice(self.user_agents)
        return self.user_agents[0]  # Default to first one
    
    def get_random_viewport(self) -> Tuple[int, int]:
        """Get random viewport size"""
        if self.config.stealth.randomize_screen_resolution:
            return random.choice(self.screen_resolutions)
        return (1920, 1080)  # Default resolution
    
    def get_random_timezone(self) -> str:
        """Get random timezone"""
        if self.config.stealth.randomize_timezone:
            return random.choice(self.timezones)
        return "America/New_York"  # Default timezone
    
    def get_random_language(self) -> str:
        """Get random language"""
        if self.config.stealth.randomize_language:
            return random.choice(self.languages)
        return "en-US,en;q=0.9"  # Default language
    
    def generate_fingerprint(self) -> Dict[str, Any]:
        """Generate a random browser fingerprint"""
        user_agent = self.get_random_user_agent()
        viewport = self.get_random_viewport()
        timezone = self.get_random_timezone()
        language = self.get_random_language()
        
        # Parse user agent to get platform info
        ua = parse_user_agent(user_agent)
        platform_name = "Windows"
        if "Mac" in ua.os.family:
            platform_name = "macOS"
        elif "Linux" in ua.os.family:
            platform_name = "Linux"
        
        platform_info = self.platforms[platform_name]
        
        fingerprint = {
            "userAgent": user_agent,
            "viewport": {"width": viewport[0], "height": viewport[1]},
            "screen": {
                "width": viewport[0],
                "height": viewport[1],
                "colorDepth": random.choice([24, 32]),
                "pixelDepth": random.choice([24, 32])
            },
            "timezone": timezone,
            "language": language,
            "platform": platform_info["platform"],
            "oscpu": platform_info["oscpu"],
            "cookieEnabled": True,
            "doNotTrack": random.choice([None, "1"]),
            "hardwareConcurrency": random.choice([2, 4, 6, 8, 12, 16]),
            "deviceMemory": random.choice([2, 4, 8, 16, 32]),
            "webgl": {
                "vendor": random.choice([
                    "Google Inc. (NVIDIA)",
                    "Google Inc. (Intel)",
                    "Google Inc. (AMD)",
                    "WebKit",
                    ""
                ]),
                "renderer": random.choice([
                    "ANGLE (NVIDIA GeForce GTX 1060 Direct3D11 vs_5_0 ps_5_0)",
                    "ANGLE (Intel(R) HD Graphics 620 Direct3D11 vs_5_0 ps_5_0)",
                    "AMD Radeon Graphics",
                    "Intel Iris Pro Graphics",
                    "WebKit WebGL"
                ])
            }
        }
        
        return fingerprint
    
    async def get_context_options(self) -> Dict[str, Any]:
        """Get browser context options with stealth settings"""
        fingerprint = self.generate_fingerprint()
        
        context_options = {
            "viewport": fingerprint["viewport"],
            "user_agent": fingerprint["userAgent"],
            "locale": fingerprint["language"].split(",")[0].replace("-", "_"),
            "timezone_id": fingerprint["timezone"],
            "permissions": self.config.browser.permissions,
            "geolocation": self.config.browser.geolocation,
            "device_scale_factor": self.config.browser.device_scale_factor,
            "is_mobile": self.config.browser.is_mobile,
            "has_touch": self.config.browser.has_touch,
            "java_script_enabled": True,
            "bypass_csp": True,
            "ignore_https_errors": True
        }
        
        return context_options
    
    async def apply_stealth_to_context(self, context) -> None:
        """Apply stealth measures to browser context"""
        if not self.config.stealth.stealth_plugin_enabled:
            return
        
        # Add init scripts to override detection
        await context.add_init_script("""
            // Override webdriver property
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
        """)
        
        await context.add_init_script("""
            // Override chrome runtime
            window.chrome = {
                runtime: {},
                loadTimes: function() {},
                csi: function() {},
                app: {}
            };
        """)
        
        await context.add_init_script("""
            // Override permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """)
        
        await context.add_init_script("""
            // Override plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
        """)
        
        await context.add_init_script("""
            // Override languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en'],
            });
        """)
        
        logger.debug("Applied stealth measures to browser context")
    
    async def apply_stealth_to_page(self, page) -> None:
        """Apply additional stealth measures to specific page"""
        if not self.config.stealth.stealth_plugin_enabled:
            return
        
        # Random mouse movements and clicks
        await self._add_human_behavior(page)
        
        # Override fingerprinting methods
        await page.add_init_script("""
            // Canvas fingerprinting protection
            const getContext = HTMLCanvasElement.prototype.getContext;
            HTMLCanvasElement.prototype.getContext = function(type) {
                if (type === '2d') {
                    const context = getContext.call(this, type);
                    const getImageData = context.getImageData;
                    context.getImageData = function(x, y, w, h) {
                        const imageData = getImageData.call(this, x, y, w, h);
                        for (let i = 0; i < imageData.data.length; i += 4) {
                            imageData.data[i] += Math.floor(Math.random() * 10) - 5;
                            imageData.data[i + 1] += Math.floor(Math.random() * 10) - 5;
                            imageData.data[i + 2] += Math.floor(Math.random() * 10) - 5;
                        }
                        return imageData;
                    };
                    return context;
                }
                return getContext.call(this, type);
            };
        """)
        
        await page.add_init_script("""
            // AudioContext fingerprinting protection
            const AudioContext = window.AudioContext || window.webkitAudioContext;
            if (AudioContext) {
                const getChannelData = AudioBuffer.prototype.getChannelData;
                AudioBuffer.prototype.getChannelData = function(channel) {
                    const originalChannelData = getChannelData.call(this, channel);
                    const fakeChannelData = new Float32Array(originalChannelData.length);
                    for (let i = 0; i < originalChannelData.length; i++) {
                        fakeChannelData[i] = originalChannelData[i] + (Math.random() - 0.5) * 0.0001;
                    }
                    return fakeChannelData;
                };
            }
        """)
        
        logger.debug("Applied page-level stealth measures")
    
    async def _add_human_behavior(self, page) -> None:
        """Add human-like behavior patterns"""
        # Random viewport jitter
        current_viewport = page.viewport_size
        if current_viewport and self.config.stealth.randomize_fingerprints:
            jitter_x = random.randint(-5, 5)
            jitter_y = random.randint(-5, 5)
            new_width = max(800, current_viewport["width"] + jitter_x)
            new_height = max(600, current_viewport["height"] + jitter_y)
            await page.set_viewport_size({"width": new_width, "height": new_height})
    
    async def random_delay(self, min_ms: int = 100, max_ms: int = 300) -> None:
        """Add random delay to mimic human timing"""
        delay = random.randint(min_ms, max_ms) / 1000.0
        await asyncio.sleep(delay)
    
    async def human_type(self, page, selector: str, text: str, delay_range: Tuple[int, int] = (50, 150)) -> None:
        """Type text with human-like delays"""
        element = await page.query_selector(selector)
        if element:
            await element.click()
            await self.random_delay(100, 300)
            
            for char in text:
                await element.type(char, delay=random.randint(delay_range[0], delay_range[1]))
                if random.random() < 0.1:  # 10% chance of pause
                    await self.random_delay(200, 500)
    
    async def human_click(self, page, selector: str, delay_before: bool = True) -> None:
        """Click with human-like behavior"""
        if delay_before:
            await self.random_delay(200, 800)
        
        element = await page.query_selector(selector)
        if element:
            # Get element bounds for realistic clicking
            box = await element.bounding_box()
            if box:
                # Click at random position within element
                x = box["x"] + random.randint(5, int(box["width"] - 5))
                y = box["y"] + random.randint(5, int(box["height"] - 5))
                
                # Move mouse to position first
                await page.mouse.move(x, y)
                await self.random_delay(50, 200)
                
                # Click
                await page.mouse.click(x, y)
            else:
                await element.click()
        
        await self.random_delay(100, 300)
    
    async def simulate_reading(self, page, min_time: int = 2000, max_time: int = 5000) -> None:
        """Simulate reading behavior with random scrolling"""
        read_time = random.randint(min_time, max_time)
        start_time = asyncio.get_event_loop().time()
        
        while (asyncio.get_event_loop().time() - start_time) * 1000 < read_time:
            # Random small scroll
            if random.random() < 0.3:
                scroll_delta = random.randint(-100, 100)
                await page.mouse.wheel(0, scroll_delta)
            
            await asyncio.sleep(random.uniform(0.5, 2.0))
    
    def get_stealth_summary(self) -> Dict[str, Any]:
        """Get summary of stealth configuration"""
        return {
            "stealth_enabled": self.config.stealth.stealth_plugin_enabled,
            "randomize_fingerprints": self.config.stealth.randomize_fingerprints,
            "randomize_user_agents": self.config.stealth.randomize_user_agents,
            "randomize_screen_resolution": self.config.stealth.randomize_screen_resolution,
            "randomize_timezone": self.config.stealth.randomize_timezone,
            "randomize_language": self.config.stealth.randomize_language,
            "navigator_override": self.config.stealth.navigator_webdriver_override,
            "chrome_runtime_override": self.config.stealth.chrome_runtime_override,
            "permissions_override": self.config.stealth.permissions_override,
            "plugins_override": self.config.stealth.plugins_override
        }


# Example usage
if __name__ == "__main__":
    import asyncio
    from .config_manager import ConfigManager
    
    async def test_stealth():
        config_manager = ConfigManager()
        stealth_manager = StealthManager(config_manager)
        
        # Generate fingerprint
        fingerprint = stealth_manager.generate_fingerprint()
        print("Generated fingerprint:")
        print(json.dumps(fingerprint, indent=2))
        
        # Get context options
        options = await stealth_manager.get_context_options()
        print("\nContext options:")
        print(json.dumps(options, indent=2, default=str))
        
        # Get stealth summary
        summary = stealth_manager.get_stealth_summary()
        print("\nStealth configuration:")
        print(json.dumps(summary, indent=2))
    
    asyncio.run(test_stealth())