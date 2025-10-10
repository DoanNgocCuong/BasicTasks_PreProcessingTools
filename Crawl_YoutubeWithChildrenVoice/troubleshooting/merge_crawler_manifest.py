#!/usr/bin/env python3
"""
Crawler Manifest Merger

Merges crawler_manifest.json into the main manifest.json with strict duplicate prevention.
Moves audio files from crawler directory to main directory.
Creates backups and clears crawler manifest after successful merge.

Usage:
    python merge_crawler_manifest.py [--dry-run]
    
    --dry-run: Show what would be merged without actually doing it
"""

import json
import shutil
import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Set, Tuple, Optional

class ManifestMerger:
    """Handles merging crawler manifest into main manifest with duplicate prevention."""
    
    def __init__(self, dry_run: bool = False):
        self.script_dir = Path(__file__).parent
        self.main_manifest_path = self.script_dir / "final_audio_files" / "manifest.json"
        self.crawler_manifest_path = self.script_dir / "crawler_outputs" / "crawler_manifest.json"
        self.main_audio_dir = self.script_dir / "final_audio_files"
        self.crawler_audio_dir = self.script_dir / "crawler_outputs" / "audio_files"
        self.dry_run = dry_run
        
        print(f"🔍 Manifest Merger initialized")
        print(f"📁 Main manifest: {self.main_manifest_path}")
        print(f"📁 Crawler manifest: {self.crawler_manifest_path}")
        print(f"📁 Main audio dir: {self.main_audio_dir}")
        print(f"📁 Crawler audio dir: {self.crawler_audio_dir}")
        if self.dry_run:
            print("🔍 DRY RUN MODE - No changes will be made")
        
    def merge_manifests(self) -> Dict:
        """Main merge operation with comprehensive duplicate prevention."""
        print("\n🔄 Starting crawler manifest merge...")
        
        # Step 1: Validate directories and files exist
        self._validate_paths()
        
        # Step 2: Load manifests
        main_data = self._load_manifest(self.main_manifest_path)
        crawler_data = self._load_manifest(self.crawler_manifest_path)
        
        print(f"📊 Main manifest records: {len(main_data.get('records', []))}")
        print(f"📊 Crawler manifest records: {len(crawler_data.get('records', []))}")
        
        if not crawler_data.get('records'):
            print("✅ No records in crawler manifest - nothing to merge")
            return {'merged_count': 0, 'message': 'No records to merge'}
        
        # Step 3: Validate no duplicates exist
        duplicates = self._find_duplicates(main_data, crawler_data)
        if duplicates:
            print("❌ Duplicates found between manifests:")
            for dup in duplicates:
                print(f"   - {dup}")
            raise ValueError(f"Cannot proceed with merge - {len(duplicates)} duplicates found")
        
        print("✅ No duplicates found - safe to proceed")
        
        if self.dry_run:
            return self._dry_run_summary(main_data, crawler_data)
        
        # Step 4: Create backups
        main_backup = self._create_backup(self.main_manifest_path)
        crawler_backup = self._create_backup(self.crawler_manifest_path)
        
        # Step 5: Process and merge records
        new_records = crawler_data.get('records', [])
        merged_count = 0
        moved_files = []
        
        for record in new_records:
            # Move audio file and update path
            if self._move_audio_file_and_update_path(record):
                main_data.setdefault('records', []).append(record)
                merged_count += 1
                moved_files.append(record.get('output_path', 'unknown'))
                print(f"✅ Merged record: {record.get('video_id', 'no-id')} - {record.get('title', 'No title')[:50]}...")
        
        # Step 6: Update totals and save
        self._update_manifest_totals(main_data)
        self._save_manifest(self.main_manifest_path, main_data)
        
        # Step 7: Clear crawler manifest
        self._clear_crawler_manifest()
        
        result = {
            'merged_count': merged_count,
            'main_backup': str(main_backup),
            'crawler_backup': str(crawler_backup),
            'moved_files': moved_files
        }
        
        print(f"\n✅ Merge completed successfully!")
        print(f"📊 Records merged: {merged_count}")
        print(f"💾 Main backup: {main_backup.name}")
        print(f"💾 Crawler backup: {crawler_backup.name}")
        
        return result
    
    def _validate_paths(self):
        """Validate all required paths exist."""
        if not self.main_manifest_path.exists():
            raise FileNotFoundError(f"Main manifest not found: {self.main_manifest_path}")
        
        if not self.crawler_manifest_path.exists():
            raise FileNotFoundError(f"Crawler manifest not found: {self.crawler_manifest_path}")
        
        if not self.main_audio_dir.exists():
            raise FileNotFoundError(f"Main audio directory not found: {self.main_audio_dir}")
        
        if not self.crawler_audio_dir.exists():
            print(f"⚠️  Crawler audio directory not found: {self.crawler_audio_dir}")
            print("   This is OK if no audio files were downloaded by crawler")
    
    def _load_manifest(self, manifest_path: Path) -> Dict:
        """Load manifest data from file."""
        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Ensure proper structure
                if isinstance(data, list):
                    return {'total_duration_seconds': 0.0, 'records': data}
                return data
        except Exception as e:
            print(f"⚠️  Error loading manifest {manifest_path}: {e}")
            return {'total_duration_seconds': 0.0, 'records': []}
    
    def _save_manifest(self, manifest_path: Path, manifest_data: Dict):
        """Save manifest data to file."""
        try:
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(manifest_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            raise RuntimeError(f"Failed to save manifest {manifest_path}: {e}")
    
    def _find_duplicates(self, main_data: Dict, crawler_data: Dict) -> List[str]:
        """Find any duplicates between manifests."""
        main_video_ids = {r.get('video_id') for r in main_data.get('records', []) if r.get('video_id')}
        main_urls = {r.get('url') for r in main_data.get('records', []) if r.get('url')}
        
        duplicates = []
        for record in crawler_data.get('records', []):
            video_id = record.get('video_id')
            url = record.get('url')
            
            if video_id and video_id in main_video_ids:
                duplicates.append(f"video_id: {video_id}")
            if url and url in main_urls:
                duplicates.append(f"url: {url}")
        
        return duplicates
    
    def _move_audio_file_and_update_path(self, record: Dict) -> bool:
        """Move audio file from crawler dir to main dir and update record path."""
        crawler_path = record.get('output_path')
        if not crawler_path:
            print(f"⚠️  Record has no output_path: {record.get('video_id', 'unknown')}")
            return False
        
        crawler_file = Path(crawler_path)
        if not crawler_file.exists():
            print(f"⚠️  Audio file not found: {crawler_path}")
            # Still include the record but mark the issue
            record['merge_note'] = 'Audio file not found during merge'
            return True
        
        # Generate new filename in main directory
        new_filename = self._generate_unique_filename(crawler_file.name)
        main_file_path = self.main_audio_dir / new_filename
        
        # Move file
        try:
            shutil.move(str(crawler_file), str(main_file_path))
            print(f"📁 Moved: {crawler_file.name} -> {new_filename}")
        except Exception as e:
            print(f"❌ Failed to move {crawler_file.name}: {e}")
            record['merge_note'] = f'Failed to move file: {e}'
            return True
        
        # Update record path
        record['output_path'] = str(main_file_path)
        record['merge_timestamp'] = datetime.now().isoformat()
        
        return True
    
    def _generate_unique_filename(self, original_name: str) -> str:
        """Generate unique filename to avoid conflicts."""
        main_file = self.main_audio_dir / original_name
        if not main_file.exists():
            return original_name
        
        # Add timestamp if conflict
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name_parts = original_name.rsplit('.', 1)
        if len(name_parts) == 2:
            return f"{name_parts[0]}_merged_{timestamp}.{name_parts[1]}"
        else:
            return f"{original_name}_merged_{timestamp}"
    
    def _create_backup(self, file_path: Path) -> Path:
        """Create backup of file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = file_path.with_suffix(f'.backup_merge_{timestamp}.json')
        shutil.copy2(file_path, backup_path)
        print(f"💾 Created backup: {backup_path.name}")
        return backup_path
    
    def _update_manifest_totals(self, manifest_data: Dict):
        """Update manifest totals."""
        records = manifest_data.get('records', [])
        total_duration = 0.0
        
        for record in records:
            duration = record.get('duration_seconds', 0)
            if isinstance(duration, (int, float)):
                total_duration += float(duration)
        
        manifest_data['total_duration_seconds'] = total_duration
        print(f"📊 Updated total duration: {total_duration:.2f} seconds ({total_duration/3600:.2f} hours)")
    
    def _clear_crawler_manifest(self):
        """Clear crawler manifest after successful merge."""
        try:
            empty_data = {
                'total_duration_seconds': 0.0,
                'records': []
            }
            self._save_manifest(self.crawler_manifest_path, empty_data)
            print("🧹 Cleared crawler manifest")
        except Exception as e:
            print(f"⚠️  Failed to clear crawler manifest: {e}")
    
    def _dry_run_summary(self, main_data: Dict, crawler_data: Dict) -> Dict:
        """Provide dry run summary without making changes."""
        crawler_records = crawler_data.get('records', [])
        
        print(f"\n🔍 DRY RUN SUMMARY:")
        print(f"📊 Records that would be merged: {len(crawler_records)}")
        print(f"📊 Current main manifest records: {len(main_data.get('records', []))}")
        print(f"📊 Total after merge would be: {len(main_data.get('records', [])) + len(crawler_records)}")
        
        # Check for audio files
        audio_files_found = 0
        audio_files_missing = 0
        
        for record in crawler_records:
            crawler_path = record.get('output_path')
            if crawler_path and Path(crawler_path).exists():
                audio_files_found += 1
            else:
                audio_files_missing += 1
        
        print(f"📁 Audio files found: {audio_files_found}")
        print(f"⚠️  Audio files missing: {audio_files_missing}")
        
        if crawler_records:
            print(f"\n📋 Sample records to merge:")
            for i, record in enumerate(crawler_records[:3]):
                video_id = record.get('video_id', 'no-id')
                title = record.get('title', 'No title')[:50]
                print(f"   {i+1}. {video_id} - {title}...")
            
            if len(crawler_records) > 3:
                print(f"   ... and {len(crawler_records) - 3} more")
        
        return {
            'dry_run': True,
            'would_merge': len(crawler_records),
            'audio_files_found': audio_files_found,
            'audio_files_missing': audio_files_missing
        }


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Merge crawler manifest into main manifest')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Show what would be merged without making changes')
    args = parser.parse_args()
    
    try:
        merger = ManifestMerger(dry_run=args.dry_run)
        result = merger.merge_manifests()
        
        if args.dry_run:
            print(f"\n✅ Dry run completed - use without --dry-run to perform actual merge")
        else:
            print(f"\n✅ Merge completed successfully!")
            print(f"🎯 Use python youtube_output_validator.py to validate/classify the merged files")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Merge failed: {e}")
        import traceback
        print(f"📋 Error details:\n{traceback.format_exc()}")
        return 1


if __name__ == "__main__":
    sys.exit(main())