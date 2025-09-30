"""
Account Management System

This module handles account storage, verification status tracking,
batch processing, and resume capability for Gmail account creation.
"""

import json
import csv
import sqlite3
import logging
import asyncio
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
import uuid

from .config_manager import ConfigManager
from .user_profile_generator import UserProfile

logger = logging.getLogger(__name__)


class AccountStatus(Enum):
    PENDING = "pending"
    CREATED = "created"
    FAILED = "failed"
    VERIFIED = "verified"
    SUSPENDED = "suspended"
    ACTIVE = "active"


class VerificationStatus(Enum):
    NOT_REQUIRED = "not_required"
    PHONE_REQUIRED = "phone_required" 
    EMAIL_REQUIRED = "email_required"
    CAPTCHA_REQUIRED = "captcha_required"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class GmailAccount:
    """Gmail account data structure"""
    id: str
    email: str
    password: str
    first_name: str
    last_name: str
    birth_date: str
    gender: str
    status: AccountStatus
    verification_status: VerificationStatus
    created_at: datetime
    last_updated: datetime
    proxy_used: Optional[str] = None
    user_agent: Optional[str] = None
    recovery_email: Optional[str] = None
    phone_number: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    locale: Optional[str] = None
    notes: Optional[str] = None
    login_attempts: int = 0
    last_login: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert account to dictionary"""
        data = asdict(self)
        # Convert enums to strings
        data['status'] = self.status.value
        data['verification_status'] = self.verification_status.value
        # Convert datetime objects to ISO strings
        data['created_at'] = self.created_at.isoformat() if self.created_at else None
        data['last_updated'] = self.last_updated.isoformat() if self.last_updated else None
        data['last_login'] = self.last_login.isoformat() if self.last_login else None
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GmailAccount':
        """Create account from dictionary"""
        # Convert string enums back to enum objects
        data['status'] = AccountStatus(data['status'])
        data['verification_status'] = VerificationStatus(data['verification_status'])
        
        # Convert ISO strings back to datetime objects
        if data.get('created_at'):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if data.get('last_updated'):
            data['last_updated'] = datetime.fromisoformat(data['last_updated'])
        if data.get('last_login'):
            data['last_login'] = datetime.fromisoformat(data['last_login'])
        
        return cls(**data)


class AccountManager:
    """Manage Gmail accounts with database storage and batch processing"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager.config
        self.config_manager = config_manager
        
        # Database setup
        self.db_path = Path(self.config.project_root) / self.config.data_dir / "accounts.db"
        self.db_path.parent.mkdir(exist_ok=True)
        
        # In-memory account cache
        self.accounts: Dict[str, GmailAccount] = {}
        
        # Batch processing state
        self.current_batch_id: Optional[str] = None
        self.batch_state_file = Path(self.config.project_root) / self.config.data_dir / "batch_state.json"
        
        # Initialize database
        self._init_database()
        
        # Load existing accounts
        self._load_accounts_from_db()
    
    def _init_database(self):
        """Initialize SQLite database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create accounts table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS accounts (
                    id TEXT PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    first_name TEXT NOT NULL,
                    last_name TEXT NOT NULL,
                    birth_date TEXT NOT NULL,
                    gender TEXT NOT NULL,
                    status TEXT NOT NULL,
                    verification_status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    last_updated TEXT NOT NULL,
                    proxy_used TEXT,
                    user_agent TEXT,
                    recovery_email TEXT,
                    phone_number TEXT,
                    country TEXT,
                    city TEXT,
                    locale TEXT,
                    notes TEXT,
                    login_attempts INTEGER DEFAULT 0,
                    last_login TEXT
                )
            """)
            
            # Create batch logs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS batch_logs (
                    batch_id TEXT PRIMARY KEY,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    total_accounts INTEGER NOT NULL,
                    successful_accounts INTEGER DEFAULT 0,
                    failed_accounts INTEGER DEFAULT 0,
                    config_snapshot TEXT,
                    status TEXT NOT NULL,
                    notes TEXT
                )
            """)
            
            # Create account_batches table for many-to-many relationship
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS account_batches (
                    account_id TEXT,
                    batch_id TEXT,
                    PRIMARY KEY (account_id, batch_id),
                    FOREIGN KEY (account_id) REFERENCES accounts(id),
                    FOREIGN KEY (batch_id) REFERENCES batch_logs(batch_id)
                )
            """)
            
            conn.commit()
            conn.close()
            
            logger.info("Database initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def _load_accounts_from_db(self):
        """Load all accounts from database into memory"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM accounts")
            rows = cursor.fetchall()
            
            # Get column names
            columns = [description[0] for description in cursor.description]
            
            for row in rows:
                account_data = dict(zip(columns, row))
                account = GmailAccount.from_dict(account_data)
                self.accounts[account.id] = account
            
            conn.close()
            
            logger.info(f"Loaded {len(self.accounts)} accounts from database")
            
        except Exception as e:
            logger.error(f"Failed to load accounts from database: {e}")
    
    def add_account(self, account: GmailAccount) -> bool:
        """Add account to manager and database"""
        try:
            # Add to memory cache
            self.accounts[account.id] = account
            
            # Add to database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            account_data = account.to_dict()
            columns = list(account_data.keys())
            placeholders = ['?' for _ in columns]
            values = list(account_data.values())
            
            cursor.execute(
                f"INSERT OR REPLACE INTO accounts ({','.join(columns)}) VALUES ({','.join(placeholders)})",
                values
            )
            
            conn.commit()
            conn.close()
            
            logger.debug(f"Added account {account.email} to database")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add account {account.email}: {e}")
            return False
    
    def update_account(self, account_id: str, **kwargs) -> bool:
        """Update account information"""
        try:
            if account_id not in self.accounts:
                logger.warning(f"Account {account_id} not found")
                return False
            
            account = self.accounts[account_id]
            
            # Update fields
            for key, value in kwargs.items():
                if hasattr(account, key):
                    setattr(account, key, value)
            
            # Update timestamp
            account.last_updated = datetime.now()
            
            # Update in database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            account_data = account.to_dict()
            set_clause = ', '.join([f"{key} = ?" for key in account_data.keys()])
            values = list(account_data.values()) + [account_id]
            
            cursor.execute(
                f"UPDATE accounts SET {set_clause} WHERE id = ?",
                values
            )
            
            conn.commit()
            conn.close()
            
            logger.debug(f"Updated account {account.email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update account {account_id}: {e}")
            return False
    
    def get_account(self, account_id: str) -> Optional[GmailAccount]:
        """Get account by ID"""
        return self.accounts.get(account_id)
    
    def get_account_by_email(self, email: str) -> Optional[GmailAccount]:
        """Get account by email address"""
        for account in self.accounts.values():
            if account.email == email:
                return account
        return None
    
    def get_accounts_by_status(self, status: AccountStatus) -> List[GmailAccount]:
        """Get all accounts with specific status"""
        return [account for account in self.accounts.values() if account.status == status]
    
    def get_accounts_by_verification_status(self, verification_status: VerificationStatus) -> List[GmailAccount]:
        """Get all accounts with specific verification status"""
        return [account for account in self.accounts.values() if account.verification_status == verification_status]
    
    def create_account_from_profile(self, user_profile: UserProfile, **kwargs) -> GmailAccount:
        """Create GmailAccount from UserProfile"""
        account_id = str(uuid.uuid4())
        
        account = GmailAccount(
            id=account_id,
            email=f"{user_profile.username}@gmail.com",
            password=user_profile.password,
            first_name=user_profile.first_name,
            last_name=user_profile.last_name,
            birth_date=f"{user_profile.birth_year}-{user_profile.birth_month:02d}-{user_profile.birth_day:02d}",
            gender=user_profile.gender,
            status=AccountStatus.PENDING,
            verification_status=VerificationStatus.NOT_REQUIRED,
            created_at=datetime.now(),
            last_updated=datetime.now(),
            country=user_profile.country,
            city=user_profile.city,
            locale=user_profile.locale,
            recovery_email=user_profile.recovery_email,
            **kwargs
        )
        
        return account
    
    def start_batch(self, total_accounts: int, notes: str = None) -> str:
        """Start a new batch processing session"""
        batch_id = str(uuid.uuid4())
        self.current_batch_id = batch_id
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO batch_logs (batch_id, start_time, total_accounts, status, config_snapshot, notes)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                batch_id,
                datetime.now().isoformat(),
                total_accounts,
                "running",
                json.dumps(self.config_manager.get_config_summary()),
                notes
            ))
            
            conn.commit()
            conn.close()
            
            # Save batch state to file
            batch_state = {
                "batch_id": batch_id,
                "start_time": datetime.now().isoformat(),
                "total_accounts": total_accounts,
                "completed_accounts": 0,
                "failed_accounts": 0,
                "status": "running"
            }
            
            with open(self.batch_state_file, 'w') as f:
                json.dump(batch_state, f, indent=2)
            
            logger.info(f"Started batch {batch_id} for {total_accounts} accounts")
            return batch_id
            
        except Exception as e:
            logger.error(f"Failed to start batch: {e}")
            raise
    
    def update_batch_progress(self, successful_count: int, failed_count: int):
        """Update batch progress"""
        if not self.current_batch_id:
            return
        
        try:
            # Update batch state file
            if self.batch_state_file.exists():
                with open(self.batch_state_file, 'r') as f:
                    batch_state = json.load(f)
                
                batch_state.update({
                    "completed_accounts": successful_count,
                    "failed_accounts": failed_count,
                    "last_updated": datetime.now().isoformat()
                })
                
                with open(self.batch_state_file, 'w') as f:
                    json.dump(batch_state, f, indent=2)
            
        except Exception as e:
            logger.error(f"Failed to update batch progress: {e}")
    
    def finish_batch(self, successful_count: int, failed_count: int, notes: str = None):
        """Finish current batch"""
        if not self.current_batch_id:
            return
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE batch_logs 
                SET end_time = ?, successful_accounts = ?, failed_accounts = ?, status = ?, notes = ?
                WHERE batch_id = ?
            """, (
                datetime.now().isoformat(),
                successful_count,
                failed_count,
                "completed",
                notes,
                self.current_batch_id
            ))
            
            conn.commit()
            conn.close()
            
            # Update batch state file
            if self.batch_state_file.exists():
                with open(self.batch_state_file, 'r') as f:
                    batch_state = json.load(f)
                
                batch_state.update({
                    "end_time": datetime.now().isoformat(),
                    "completed_accounts": successful_count,
                    "failed_accounts": failed_count,
                    "status": "completed"
                })
                
                with open(self.batch_state_file, 'w') as f:
                    json.dump(batch_state, f, indent=2)
            
            logger.info(f"Finished batch {self.current_batch_id}: {successful_count} successful, {failed_count} failed")
            self.current_batch_id = None
            
        except Exception as e:
            logger.error(f"Failed to finish batch: {e}")
    
    def can_resume_batch(self) -> bool:
        """Check if there's a batch that can be resumed"""
        if not self.batch_state_file.exists():
            return False
        
        try:
            with open(self.batch_state_file, 'r') as f:
                batch_state = json.load(f)
            
            return batch_state.get('status') == 'running'
            
        except Exception as e:
            logger.error(f"Failed to check batch resume status: {e}")
            return False
    
    def get_batch_resume_info(self) -> Optional[Dict[str, Any]]:
        """Get information about batch that can be resumed"""
        if not self.can_resume_batch():
            return None
        
        try:
            with open(self.batch_state_file, 'r') as f:
                return json.load(f)
                
        except Exception as e:
            logger.error(f"Failed to get batch resume info: {e}")
            return None
    
    def resume_batch(self) -> Optional[str]:
        """Resume interrupted batch"""
        batch_info = self.get_batch_resume_info()
        if not batch_info:
            return None
        
        self.current_batch_id = batch_info['batch_id']
        logger.info(f"Resumed batch {self.current_batch_id}")
        return self.current_batch_id
    
    def export_accounts(self, file_path: str, format_type: str = "json", status_filter: AccountStatus = None) -> bool:
        """Export accounts to file"""
        try:
            accounts_to_export = list(self.accounts.values())
            
            if status_filter:
                accounts_to_export = [acc for acc in accounts_to_export if acc.status == status_filter]
            
            if format_type.lower() == "json":
                data = [account.to_dict() for account in accounts_to_export]
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
            
            elif format_type.lower() == "csv":
                if accounts_to_export:
                    with open(file_path, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.DictWriter(f, fieldnames=accounts_to_export[0].to_dict().keys())
                        writer.writeheader()
                        for account in accounts_to_export:
                            writer.writerow(account.to_dict())
            
            elif format_type.lower() == "txt":
                with open(file_path, 'w', encoding='utf-8') as f:
                    for account in accounts_to_export:
                        if account.status == AccountStatus.CREATED:
                            f.write(f"{account.email}:{account.password}\n")
            
            logger.info(f"Exported {len(accounts_to_export)} accounts to {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export accounts: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get account statistics"""
        total = len(self.accounts)
        status_counts = {}
        verification_counts = {}
        
        for status in AccountStatus:
            status_counts[status.value] = len(self.get_accounts_by_status(status))
        
        for verification_status in VerificationStatus:
            verification_counts[verification_status.value] = len(
                self.get_accounts_by_verification_status(verification_status)
            )
        
        # Calculate success rate
        created_count = status_counts.get(AccountStatus.CREATED.value, 0)
        failed_count = status_counts.get(AccountStatus.FAILED.value, 0)
        success_rate = (created_count / (created_count + failed_count) * 100) if (created_count + failed_count) > 0 else 0
        
        return {
            "total_accounts": total,
            "status_breakdown": status_counts,
            "verification_breakdown": verification_counts,
            "success_rate": success_rate,
            "last_updated": datetime.now().isoformat()
        }
    
    def cleanup_old_batches(self, days_old: int = 30):
        """Clean up old batch logs"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_old)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                DELETE FROM batch_logs 
                WHERE start_time < ? AND status = 'completed'
            """, (cutoff_date.isoformat(),))
            
            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()
            
            logger.info(f"Cleaned up {deleted_count} old batch logs")
            
        except Exception as e:
            logger.error(f"Failed to cleanup old batches: {e}")


# Example usage
if __name__ == "__main__":
    from .config_manager import ConfigManager
    from .user_profile_generator import UserProfileGenerator
    
    # Initialize
    config_manager = ConfigManager()
    config_manager.setup_logging()
    
    account_manager = AccountManager(config_manager)
    user_generator = UserProfileGenerator(config_manager)
    
    # Create test account
    profile = user_generator.generate_profile()
    account = account_manager.create_account_from_profile(profile)
    account.status = AccountStatus.CREATED
    
    # Add to manager
    account_manager.add_account(account)
    
    # Get statistics
    stats = account_manager.get_statistics()
    print("Account Statistics:")
    print(json.dumps(stats, indent=2))
    
    # Export accounts
    account_manager.export_accounts("test_accounts.json", "json")
    print("Accounts exported successfully")