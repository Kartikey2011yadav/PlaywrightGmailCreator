"""
Main Entry Point for Advanced Gmail Creator

This is the main script that orchestrates all components and provides
a command-line interface for Gmail account creation.
"""

import asyncio
import argparse
import sys
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

# Import our modules
from src.config_manager import ConfigManager, LogLevel
from src.gmail_creator import GmailCreator
from src.account_manager import AccountManager, AccountStatus
from src.user_profile_generator import UserProfileGenerator
from src.proxy_manager import ProxyManager, FreeProxyFetcher

logger = logging.getLogger(__name__)


class GmailCreatorApp:
    """Main application class"""
    
    def __init__(self, config_file: Optional[str] = None):
        # Initialize configuration
        self.config_manager = ConfigManager(config_file)
        self.config = self.config_manager.load_config()
        
        # Setup logging
        self.logger = self.config_manager.setup_logging()
        self.config_manager.create_directories()
        
        # Initialize components
        self.account_manager = AccountManager(self.config_manager)
        self.user_generator = UserProfileGenerator(self.config_manager)
        self.gmail_creator = GmailCreator(self.config_manager)
        
        self.logger.info("Gmail Creator Application initialized")
    
    async def run_creation_batch(self, count: int, resume: bool = False) -> Dict[str, Any]:
        """Run a batch of Gmail account creations"""
        try:
            # Check for resume capability
            if resume and self.account_manager.can_resume_batch():
                batch_info = self.account_manager.get_batch_resume_info()
                self.logger.info(f"Resuming batch: {batch_info}")
                self.account_manager.resume_batch()
                # Adjust count based on already completed accounts
                remaining = batch_info['total_accounts'] - batch_info['completed_accounts']
                count = min(count, remaining)
            
            if count <= 0:
                self.logger.info("No accounts to create")
                return {"status": "completed", "message": "No accounts to create"}
            
            # Initialize Gmail creator
            await self.gmail_creator.initialize()
            
            # Start batch tracking
            if not resume:
                batch_id = self.account_manager.start_batch(
                    count, 
                    f"Automated batch creation of {count} accounts"
                )
            
            # Create accounts
            self.logger.info(f"Starting creation of {count} Gmail accounts")
            results = await self.gmail_creator.create_bulk_accounts(count)
            
            # Process results and update account manager
            successful_accounts = []
            failed_accounts = []
            
            for i, result in enumerate(results):
                try:
                    if result.get('status') == 'created':
                        # Create account object from result
                        profile = self.user_generator.generate_profile()  # This should be the actual profile used
                        account = self.account_manager.create_account_from_profile(
                            profile,
                            proxy_used=result.get('proxy_used'),
                            user_agent=result.get('user_agent'),
                            status=AccountStatus.CREATED
                        )
                        
                        # Override with actual data from result
                        account.email = result['email']
                        account.password = result['password']
                        account.first_name = result['first_name']
                        account.last_name = result['last_name']
                        
                        self.account_manager.add_account(account)
                        successful_accounts.append(account)
                        
                    else:
                        # Handle failed account
                        failed_accounts.append(result)
                        
                except Exception as e:
                    self.logger.error(f"Error processing result {i}: {e}")
                    failed_accounts.append({"error": str(e), "index": i})
            
            # Update batch progress
            self.account_manager.update_batch_progress(len(successful_accounts), len(failed_accounts))
            
            # Finish batch
            self.account_manager.finish_batch(
                len(successful_accounts), 
                len(failed_accounts),
                f"Batch completed: {len(successful_accounts)} successful, {len(failed_accounts)} failed"
            )
            
            # Generate summary
            summary = {
                "status": "completed",
                "total_requested": count,
                "successful_accounts": len(successful_accounts),
                "failed_accounts": len(failed_accounts),
                "success_rate": (len(successful_accounts) / count * 100) if count > 0 else 0,
                "accounts": [acc.to_dict() for acc in successful_accounts],
                "failures": failed_accounts,
                "timestamp": datetime.now().isoformat()
            }
            
            self.logger.info(f"Batch creation completed: {len(successful_accounts)}/{count} successful")
            return summary
            
        except Exception as e:
            self.logger.error(f"Error in batch creation: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def test_proxies(self) -> Dict[str, Any]:
        """Test proxy connectivity"""
        try:
            self.logger.info("Testing proxy connectivity...")
            
            if not self.config.proxy.enabled:
                return {"status": "skipped", "message": "Proxy not enabled"}
            
            # Initialize proxy manager
            proxy_manager = ProxyManager()
            
            if self.config.proxy.auto_fetch_free:
                proxy_manager = await FreeProxyFetcher.fetch_and_setup_manager()
            elif self.config.proxy.proxy_file:
                proxy_manager.load_proxies_from_file(self.config.proxy.proxy_file)
                await proxy_manager.test_all_proxies()
            elif self.config.proxy.proxy_list:
                proxy_manager.load_proxies_from_list(self.config.proxy.proxy_list)
                await proxy_manager.test_all_proxies()
            else:
                return {"status": "error", "message": "No proxy source configured"}
            
            stats = proxy_manager.get_proxy_stats()
            
            self.logger.info(f"Proxy test completed: {stats['active']}/{stats['total']} proxies active")
            return {
                "status": "completed",
                "proxy_stats": stats,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error testing proxies: {e}")
            return {"status": "error", "error": str(e)}
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get application statistics"""
        try:
            account_stats = self.account_manager.get_statistics()
            config_summary = self.config_manager.get_config_summary()
            
            return {
                "account_statistics": account_stats,
                "configuration": config_summary,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting statistics: {e}")
            return {"status": "error", "error": str(e)}
    
    def export_accounts(self, output_file: str, format_type: str = "json", status_filter: str = None) -> Dict[str, Any]:
        """Export accounts to file"""
        try:
            status_enum = None
            if status_filter:
                try:
                    status_enum = AccountStatus(status_filter.lower())
                except ValueError:
                    return {"status": "error", "error": f"Invalid status filter: {status_filter}"}
            
            success = self.account_manager.export_accounts(output_file, format_type, status_enum)
            
            if success:
                return {
                    "status": "success",
                    "message": f"Accounts exported to {output_file}",
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {"status": "error", "error": "Export failed"}
                
        except Exception as e:
            self.logger.error(f"Error exporting accounts: {e}")
            return {"status": "error", "error": str(e)}
    
    def validate_configuration(self) -> Dict[str, Any]:
        """Validate current configuration"""
        try:
            errors = self.config_manager.validate_config()
            
            if errors:
                return {
                    "status": "invalid",
                    "errors": errors,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "status": "valid",
                    "message": "Configuration is valid",
                    "summary": self.config_manager.get_config_summary(),
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            self.logger.error(f"Error validating configuration: {e}")
            return {"status": "error", "error": str(e)}


def create_argument_parser() -> argparse.ArgumentParser:
    """Create command line argument parser"""
    parser = argparse.ArgumentParser(
        description="Advanced Gmail Account Creator with Playwright",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py create 5                    # Create 5 Gmail accounts
  python main.py create 10 --resume          # Create 10 accounts with resume capability
  python main.py test-proxies                # Test proxy connectivity
  python main.py stats                       # Show statistics
  python main.py export accounts.json json   # Export accounts to JSON
  python main.py validate                    # Validate configuration
        """
    )
    
    # Global options
    parser.add_argument("--config", "-c", help="Configuration file path")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    parser.add_argument("--quiet", "-q", action="store_true", help="Quiet mode (errors only)")
    
    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Create command
    create_parser = subparsers.add_parser("create", help="Create Gmail accounts")
    create_parser.add_argument("count", type=int, help="Number of accounts to create")
    create_parser.add_argument("--resume", "-r", action="store_true", help="Resume interrupted batch")
    create_parser.add_argument("--output", "-o", help="Output file for results")
    
    # Test proxies command
    subparsers.add_parser("test-proxies", help="Test proxy connectivity")
    
    # Statistics command
    subparsers.add_parser("stats", help="Show account statistics")
    
    # Export command
    export_parser = subparsers.add_parser("export", help="Export accounts")
    export_parser.add_argument("output_file", help="Output file path")
    export_parser.add_argument("format", choices=["json", "csv", "txt"], help="Export format")
    export_parser.add_argument("--status", help="Filter by account status")
    
    # Validate command
    subparsers.add_parser("validate", help="Validate configuration")
    
    return parser


async def main():
    """Main application entry point"""
    parser = create_argument_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        # Initialize application
        app = GmailCreatorApp(args.config)
        
        # Adjust logging level based on arguments
        if args.verbose:
            logging.getLogger().setLevel(logging.DEBUG)
        elif args.quiet:
            logging.getLogger().setLevel(logging.ERROR)
        
        # Execute command
        if args.command == "create":
            result = await app.run_creation_batch(args.count, args.resume)
            
            if args.output:
                with open(args.output, 'w') as f:
                    json.dump(result, f, indent=2)
                print(f"Results saved to {args.output}")
            else:
                print(json.dumps(result, indent=2))
        
        elif args.command == "test-proxies":
            result = await app.test_proxies()
            print(json.dumps(result, indent=2))
        
        elif args.command == "stats":
            result = app.get_statistics()
            print(json.dumps(result, indent=2))
        
        elif args.command == "export":
            result = app.export_accounts(args.output_file, args.format, args.status)
            print(json.dumps(result, indent=2))
        
        elif args.command == "validate":
            result = app.validate_configuration()
            print(json.dumps(result, indent=2))
            
            if result["status"] != "valid":
                sys.exit(1)
    
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    
    except Exception as e:
        print(f"Fatal error: {e}")
        logging.getLogger().error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    # Set up asyncio for Windows compatibility
    if sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    # Run the application
    asyncio.run(main())