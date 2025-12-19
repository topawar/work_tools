"""
Database Manager for Portable EXE Packaging

This module provides the DatabaseManager class that handles SQLite database
operations for the portable executable, including database copying, integrity
verification, and path management.

**Feature: portable-exe-packaging**
**Requirements: 1.2, 2.3, 2.4**
"""

import os
import sys
import sqlite3
import shutil
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional, Union, Dict, Any
import logging


class DatabaseManager:
    """
    Manages SQLite database operations for the portable application.
    
    Handles database initialization, copying existing databases, integrity
    verification, and ensures all database operations use relative paths.
    """
    
    def __init__(self, db_path: Union[str, Path], source_db_path: Optional[Union[str, Path]] = None):
        """
        Initialize DatabaseManager with database paths.
        
        Args:
            db_path: Path to the target database file (relative to executable).
            source_db_path: Optional path to source database to copy from.
        """
        self.db_path = Path(db_path)
        self.source_db_path = Path(source_db_path) if source_db_path else None
        
        # Set up logging
        self.logger = logging.getLogger('app.database_manager')
        
        # Ensure parent directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
    
    def initialize_database(self) -> bool:
        """
        Initialize the database for the portable application.
        
        If a source database exists, copies it to the target location.
        Otherwise, creates a new empty database.
        
        Returns:
            True if initialization successful, False otherwise.
        """
        try:
            # If source database exists and target doesn't, copy it
            if (self.source_db_path and 
                self.source_db_path.exists() and 
                not self.db_path.exists()):
                
                self.logger.info(f"Copying database from {self.source_db_path} to {self.db_path}")
                return self.copy_existing_database()
            
            # If target database doesn't exist, create it
            elif not self.db_path.exists():
                self.logger.info(f"Creating new database at {self.db_path}")
                return self._create_empty_database()
            
            # Database already exists, verify integrity
            else:
                self.logger.info(f"Database already exists at {self.db_path}, verifying integrity")
                return self.verify_database_integrity()
                
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
            return False
    
    def copy_existing_database(self) -> bool:
        """
        Copy existing database file to the target location.
        
        Performs integrity verification on both source and copied database
        to ensure consistency.
        
        Returns:
            True if copy successful and consistent, False otherwise.
        """
        if not self.source_db_path or not self.source_db_path.exists():
            self.logger.error(f"Source database not found: {self.source_db_path}")
            return False
        
        try:
            # Verify source database integrity first
            if not self._verify_database_file(self.source_db_path):
                self.logger.error(f"Source database integrity check failed: {self.source_db_path}")
                return False
            
            # Get source database checksum
            source_checksum = self._calculate_file_checksum(self.source_db_path)
            
            # Copy the database file
            shutil.copy2(self.source_db_path, self.db_path)
            self.logger.info(f"Database copied from {self.source_db_path} to {self.db_path}")
            
            # Verify copied database checksum
            target_checksum = self._calculate_file_checksum(self.db_path)
            
            if source_checksum != target_checksum:
                self.logger.error("Database copy checksum mismatch")
                return False
            
            # Verify copied database integrity
            if not self.verify_database_integrity():
                self.logger.error("Copied database integrity verification failed")
                return False
            
            self.logger.info("Database copy completed successfully with integrity verification")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to copy database: {e}")
            return False
    
    def verify_database_integrity(self) -> bool:
        """
        Verify database integrity using SQLite's built-in integrity check.
        
        Returns:
            True if database integrity is valid, False otherwise.
        """
        return self._verify_database_file(self.db_path)
    
    def _verify_database_file(self, db_file_path: Path) -> bool:
        """
        Verify integrity of a specific database file.
        
        Args:
            db_file_path: Path to the database file to verify.
        
        Returns:
            True if database integrity is valid, False otherwise.
        """
        if not db_file_path.exists():
            self.logger.error(f"Database file not found: {db_file_path}")
            return False
        
        try:
            # Connect to database and run integrity check
            with sqlite3.connect(str(db_file_path)) as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA integrity_check")
                result = cursor.fetchone()
                
                if result and result[0] == 'ok':
                    self.logger.debug(f"Database integrity check passed: {db_file_path}")
                    return True
                else:
                    self.logger.error(f"Database integrity check failed: {db_file_path}, result: {result}")
                    return False
                    
        except sqlite3.Error as e:
            self.logger.error(f"Database integrity check error for {db_file_path}: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error during integrity check for {db_file_path}: {e}")
            return False
    
    def _create_empty_database(self) -> bool:
        """
        Create an empty SQLite database file.
        
        Returns:
            True if database creation successful, False otherwise.
        """
        try:
            # Create empty database
            with sqlite3.connect(str(self.db_path)) as conn:
                # Create a simple table to ensure database is valid
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS _database_info (
                        key TEXT PRIMARY KEY,
                        value TEXT
                    )
                """)
                cursor.execute("""
                    INSERT OR REPLACE INTO _database_info (key, value) 
                    VALUES ('created_by', 'DatabaseManager')
                """)
                conn.commit()
            
            self.logger.info(f"Empty database created successfully: {self.db_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create empty database: {e}")
            return False
    
    def _calculate_file_checksum(self, file_path: Path) -> str:
        """
        Calculate SHA-256 checksum of a file.
        
        Args:
            file_path: Path to the file.
        
        Returns:
            SHA-256 checksum as hexadecimal string.
        """
        sha256_hash = hashlib.sha256()
        
        with open(file_path, "rb") as f:
            # Read file in chunks to handle large files
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        
        return sha256_hash.hexdigest()
    
    def get_database_info(self) -> Dict[str, Any]:
        """
        Get information about the database.
        
        Returns:
            Dictionary containing database information.
        """
        info = {
            'db_path': str(self.db_path),
            'exists': self.db_path.exists(),
            'size': None,
            'integrity_ok': False,
            'tables': []
        }
        
        if self.db_path.exists():
            try:
                info['size'] = self.db_path.stat().st_size
                info['integrity_ok'] = self.verify_database_integrity()
                
                # Get table list
                with sqlite3.connect(str(self.db_path)) as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    info['tables'] = [row[0] for row in cursor.fetchall()]
                    
            except Exception as e:
                self.logger.error(f"Error getting database info: {e}")
        
        return info
    
    def backup_database(self, backup_path: Optional[Union[str, Path]] = None) -> bool:
        """
        Create a backup of the current database.
        
        Args:
            backup_path: Optional path for backup. If None, creates backup 
                        with timestamp suffix.
        
        Returns:
            True if backup successful, False otherwise.
        """
        if not self.db_path.exists():
            self.logger.error("Cannot backup non-existent database")
            return False
        
        try:
            if backup_path is None:
                # Create backup with timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = self.db_path.with_suffix(f'.backup_{timestamp}.sqlite3')
            else:
                backup_path = Path(backup_path)
            
            # Copy database to backup location
            shutil.copy2(self.db_path, backup_path)
            
            # Verify backup integrity
            if self._verify_database_file(backup_path):
                self.logger.info(f"Database backup created successfully: {backup_path}")
                return True
            else:
                self.logger.error(f"Backup integrity verification failed: {backup_path}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to create database backup: {e}")
            return False
    
    def __str__(self) -> str:
        """String representation of DatabaseManager."""
        return f"DatabaseManager(db_path={self.db_path}, source={self.source_db_path})"
    
    def __repr__(self) -> str:
        """Detailed representation of DatabaseManager."""
        return (f"DatabaseManager(db_path={self.db_path}, "
                f"source_db_path={self.source_db_path}, "
                f"exists={self.db_path.exists()})")