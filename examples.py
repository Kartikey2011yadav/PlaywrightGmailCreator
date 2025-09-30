#!/usr/bin/env python3
"""
Example Usage of Gmail Creator

This script demonstrates various ways to use the Gmail Creator
with different configurations and scenarios.
"""

import asyncio
import json
import logging
from pathlib import Path

# Import our modules
from src.config_manager import ConfigManager
from src.gmail_creator import GmailCreator
from src.account_manager import AccountManager, AccountStatus
from src.user_profile_generator import UserProfileGenerator
from src.proxy_manager import ProxyManager


async def example_basic_usage():
    """Basic usage example - create 3 accounts with default settings"""
    print("=" * 60)
    print("EXAMPLE 1: Basic Usage")
    print("=" * 60)
    
    # Initialize with default configuration
    config_manager = ConfigManager()
    logger = config_manager.setup_logging()
    
    # Create Gmail creator
    creator = GmailCreator(config_manager)
    await creator.initialize()
    
    # Create 3 accounts
    print("Creating 3 Gmail accounts with default settings...")
    results = await creator.create_bulk_accounts(3)
    
    # Display results
    successful = [r for r in results if r.get('status') == 'created']
    failed = [r for r in results if r.get('status') != 'created']
    
    print(f"\n✅ Successfully created: {len(successful)} accounts")
    print(f"❌ Failed: {len(failed)} accounts")
    
    for account in successful:
        print(f"   📧 {account['email']} : {account['password']}")


async def example_with_proxies():
    """Example using proxy configuration"""
    print("\n" + "=" * 60)
    print("EXAMPLE 2: Using Proxies")
    print("=" * 60)
    
    # Load advanced configuration with proxies
    config_manager = ConfigManager("config/advanced_config.yaml")
    logger = config_manager.setup_logging()
    
    # Test proxy connectivity first
    print("Testing proxy connectivity...")
    proxy_manager = ProxyManager()
    
    # Add some example proxies (replace with real ones)
    example_proxies = [
        "proxy1.example.com:8080",
        "proxy2.example.com:3128",
    ]
    
    if example_proxies:
        proxy_manager.load_proxies_from_list(example_proxies)
        await proxy_manager.test_all_proxies()
        
        stats = proxy_manager.get_proxy_stats()
        print(f"Proxy Status: {stats['active']}/{stats['total']} active")
        
        if stats['active'] > 0:
            # Create accounts with proxies
            creator = GmailCreator(config_manager)
            creator.proxy_manager = proxy_manager
            
            print("Creating 2 accounts with proxy rotation...")
            results = await creator.create_bulk_accounts(2)
            
            for result in results:
                if result.get('status') == 'created':
                    print(f"✅ Created with proxy: {result['email']}")
                else:
                    print(f"❌ Failed: {result.get('error', 'Unknown error')}")
        else:
            print("❌ No active proxies available")
    else:
        print("⚠️  No proxies configured - skipping proxy example")


async def example_account_management():
    """Example of account management features"""
    print("\n" + "=" * 60)
    print("EXAMPLE 3: Account Management")
    print("=" * 60)
    
    config_manager = ConfigManager()
    account_manager = AccountManager(config_manager)
    
    # Get statistics
    stats = account_manager.get_statistics()
    print("Account Statistics:")
    print(json.dumps(stats, indent=2))
    
    # Get accounts by status
    created_accounts = account_manager.get_accounts_by_status(AccountStatus.CREATED)
    print(f"\nFound {len(created_accounts)} created accounts")
    
    # Export accounts if any exist
    if created_accounts:
        print("Exporting created accounts...")
        
        # Export to different formats
        account_manager.export_accounts("example_output.json", "json", AccountStatus.CREATED)
        account_manager.export_accounts("example_output.csv", "csv", AccountStatus.CREATED)
        account_manager.export_accounts("example_credentials.txt", "txt", AccountStatus.CREATED)
        
        print("✅ Accounts exported to multiple formats")
    else:
        print("ℹ️  No created accounts to export")


def example_user_profiles():
    """Example of user profile generation"""
    print("\n" + "=" * 60)
    print("EXAMPLE 4: User Profile Generation")
    print("=" * 60)
    
    config_manager = ConfigManager()
    generator = UserProfileGenerator(config_manager)
    
    # Generate 5 diverse profiles
    print("Generating 5 diverse user profiles...")
    profiles = generator.generate_multiple_profiles(5)
    
    for i, profile in enumerate(profiles, 1):
        print(f"\nProfile {i}:")
        print(f"  Name: {profile.full_name}")
        print(f"  Username: {profile.username}")
        print(f"  Email: {profile.username}@gmail.com")
        print(f"  Age: {profile.age}")
        print(f"  Location: {profile.city}, {profile.country}")
        print(f"  Locale: {profile.locale}")
        print(f"  Gender: {profile.gender}")
    
    # Save profiles to file
    generator.save_profiles_to_file(profiles, "example_profiles.json")
    print(f"\n✅ Profiles saved to example_profiles.json")


async def example_batch_processing():
    """Example of batch processing with resume capability"""
    print("\n" + "=" * 60)
    print("EXAMPLE 5: Batch Processing")
    print("=" * 60)
    
    config_manager = ConfigManager()
    account_manager = AccountManager(config_manager)
    
    # Check if there's a batch to resume
    if account_manager.can_resume_batch():
        print("Found interrupted batch - resuming...")
        batch_info = account_manager.get_batch_resume_info()
        print(f"Batch info: {json.dumps(batch_info, indent=2)}")
        
        # Resume batch
        batch_id = account_manager.resume_batch()
        print(f"Resumed batch: {batch_id}")
    else:
        print("No interrupted batch found - starting new batch")
        
        # Start new batch
        batch_id = account_manager.start_batch(5, "Example batch processing")
        print(f"Started new batch: {batch_id}")
        
        # Simulate some progress
        account_manager.update_batch_progress(2, 1)
        
        # Finish batch
        account_manager.finish_batch(2, 1, "Example batch completed")
        print("✅ Batch processing example completed")


def example_configuration():
    """Example of configuration management"""
    print("\n" + "=" * 60)
    print("EXAMPLE 6: Configuration Management")
    print("=" * 60)
    
    # Load different configurations
    configs = [
        ("Default Config", None),
        ("Minimal Config", "config/minimal_config.yaml"),
        ("Advanced Config", "config/advanced_config.yaml")
    ]
    
    for name, config_file in configs:
        try:
            print(f"\n{name}:")
            config_manager = ConfigManager(config_file)
            config = config_manager.load_config()
            
            # Validate configuration
            errors = config_manager.validate_config()
            if errors:
                print(f"  ❌ Validation errors: {errors}")
            else:
                print("  ✅ Configuration is valid")
            
            # Show summary
            summary = config_manager.get_config_summary()
            print(f"  Summary: {json.dumps(summary, indent=4)}")
            
        except Exception as e:
            print(f"  ❌ Error loading {name}: {e}")


async def main():
    """Main example function"""
    print("🚀 Gmail Creator - Advanced Examples")
    print("=====================================")
    
    try:
        # Run examples
        await example_basic_usage()
        await example_with_proxies() 
        await example_account_management()
        example_user_profiles()
        await example_batch_processing()
        example_configuration()
        
        print("\n" + "=" * 60)
        print("✅ All examples completed successfully!")
        print("=" * 60)
        
        print("\n📚 What's Next?")
        print("- Review the generated files in output/ directory")
        print("- Customize config/config.yaml for your needs")
        print("- Run 'python main.py create 5' to create accounts")
        print("- Check README.md for detailed documentation")
        
    except KeyboardInterrupt:
        print("\n⏹️  Examples interrupted by user")
    except Exception as e:
        print(f"\n❌ Error in examples: {e}")
        logging.getLogger().error(f"Error in examples: {e}", exc_info=True)


if __name__ == "__main__":
    # Run examples
    asyncio.run(main())