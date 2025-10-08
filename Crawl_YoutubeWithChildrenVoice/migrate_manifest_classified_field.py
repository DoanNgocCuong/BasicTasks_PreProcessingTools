#!/usr/bin/env python3
"""
Manifest Migration Script: Add 'classified' Field

This script migrates existing manifest.json files to include the new 'classified' field.
All existing entries are marked as classified=true since they were manually curated
and represent children's voices.

Author: Le Hoang Minh
"""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any


class ManifestMigrator:
    """Handles migration of manifest.json files to include classified field."""
    
    def __init__(self, manifest_path: Path):
        """
        Initialize migrator with manifest path.
        
        Args:
            manifest_path (Path): Path to manifest.json file
        """
        self.manifest_path = manifest_path
        self.backup_path = manifest_path.with_suffix(f'.json.backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
    
    def create_backup(self) -> bool:
        """
        Create backup of original manifest file.
        
        Returns:
            bool: True if backup successful, False otherwise
        """
        try:
            if not self.manifest_path.exists():
                print(f"❌ Manifest file not found: {self.manifest_path}")
                return False
            
            shutil.copy2(self.manifest_path, self.backup_path)
            print(f"✅ Backup created: {self.backup_path}")
            return True
        except Exception as e:
            print(f"❌ Failed to create backup: {e}")
            return False
    
    def load_manifest(self) -> Dict[str, Any]:
        """
        Load manifest.json file.
        
        Returns:
            Dict[str, Any]: Manifest data or empty dict if failed
        """
        try:
            with self.manifest_path.open('r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Failed to load manifest: {e}")
            return {}
    
    def migrate_records(self, manifest_data: Dict[str, Any]) -> int:
        """
        Add classified field to all records.
        
        Args:
            manifest_data (Dict[str, Any]): Manifest data to migrate
            
        Returns:
            int: Number of records migrated
        """
        records = manifest_data.get('records', [])
        migrated_count = 0
        current_timestamp = datetime.now().isoformat()
        
        for record in records:
            # Only add classified field if it doesn't exist
            if 'classified' not in record:
                record['classified'] = True
                record['classification_timestamp'] = current_timestamp
                migrated_count += 1
            elif record.get('classified') is None:
                # Handle cases where classified exists but is null
                record['classified'] = True
                record['classification_timestamp'] = current_timestamp
                migrated_count += 1
        
        return migrated_count
    
    def save_manifest(self, manifest_data: Dict[str, Any]) -> bool:
        """
        Save migrated manifest data.
        
        Args:
            manifest_data (Dict[str, Any]): Manifest data to save
            
        Returns:
            bool: True if save successful, False otherwise
        """
        try:
            with self.manifest_path.open('w', encoding='utf-8') as f:
                json.dump(manifest_data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"❌ Failed to save manifest: {e}")
            return False
    
    def validate_migration(self, manifest_data: Dict[str, Any]) -> bool:
        """
        Validate that migration was successful.
        
        Args:
            manifest_data (Dict[str, Any]): Migrated manifest data
            
        Returns:
            bool: True if validation passed, False otherwise
        """
        records = manifest_data.get('records', [])
        
        for i, record in enumerate(records):
            if 'classified' not in record:
                print(f"❌ Validation failed: Record {i} missing 'classified' field")
                return False
            if not isinstance(record['classified'], bool):
                print(f"❌ Validation failed: Record {i} 'classified' field is not boolean")
                return False
        
        print(f"✅ Validation passed: All {len(records)} records have 'classified' field")
        return True
    
    def run_migration(self) -> bool:
        """
        Run complete migration process.
        
        Returns:
            bool: True if migration successful, False otherwise
        """
        print("🚀 Starting manifest migration...")
        print(f"📁 Manifest file: {self.manifest_path}")
        
        # Create backup
        if not self.create_backup():
            return False
        
        # Load manifest
        manifest_data = self.load_manifest()
        if not manifest_data:
            return False
        
        # Show pre-migration stats
        total_records = len(manifest_data.get('records', []))
        print(f"📊 Total records in manifest: {total_records}")
        
        # Migrate records
        migrated_count = self.migrate_records(manifest_data)
        print(f"🔄 Migrated {migrated_count} records")
        
        # Save migrated manifest
        if not self.save_manifest(manifest_data):
            print("❌ Migration failed during save")
            return False
        
        # Validate migration
        if not self.validate_migration(manifest_data):
            print("❌ Migration failed validation")
            return False
        
        print("✅ Migration completed successfully!")
        print(f"💾 Backup saved as: {self.backup_path}")
        return True


def main():
    """Main function to run the migration."""
    print("🎯 Manifest Migration Tool")
    print("=" * 50)
    
    # Default manifest path
    script_dir = Path(__file__).parent
    manifest_path = script_dir / "final_audio_files" / "manifest.json"
    
    # Check if manifest exists
    if not manifest_path.exists():
        print(f"❌ Manifest file not found: {manifest_path}")
        print("Please ensure the manifest.json file exists in the expected location.")
        return False
    
    # Run migration
    migrator = ManifestMigrator(manifest_path)
    success = migrator.run_migration()
    
    if success:
        print("\n🎉 Migration completed successfully!")
        print("📋 Summary:")
        print("   • All existing records marked as classified=true")
        print("   • Classification timestamp added to each record")
        print("   • Original file backed up")
        print("   • Ready for output validator classification of new entries")
    else:
        print("\n❌ Migration failed!")
        print("Please check the error messages above and try again.")
    
    return success


if __name__ == "__main__":
    main()
