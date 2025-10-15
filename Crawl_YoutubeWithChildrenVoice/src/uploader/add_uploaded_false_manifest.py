"""
Script to add 'uploaded: false' field to records in manifest.json that do not have an 'uploaded' field yet.

This script creates a backup of the manifest file before modifying it,
then adds the 'uploaded' field set to false for records that are missing it.
"""

import json
import shutil
from datetime import datetime
from pathlib import Path


def create_backup(manifest_path: Path, backup_dir: Path) -> Path:
    """
    Create a backup of the manifest file with timestamp.

    Args:
        manifest_path: Path to the manifest file
        backup_dir: Directory to store the backup

    Returns:
        Path to the created backup file
    """
    # Ensure backup directory exists
    backup_dir.mkdir(parents=True, exist_ok=True)

    # Create backup filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"{manifest_path.stem}_backup_{timestamp}{manifest_path.suffix}"
    backup_path = backup_dir / backup_name

    # Copy the file
    shutil.copy2(manifest_path, backup_path)
    print(f"Created backup: {backup_path}")

    return backup_path


def add_uploaded_false_field(manifest_path: Path) -> None:
    """
    Add 'uploaded: false' field to records in the manifest that do not have it.

    Args:
        manifest_path: Path to the manifest file
    """
    # Load the manifest
    with open(manifest_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Add 'uploaded': false to records that don't have it
    if 'records' in data:
        modified_count = 0
        for record in data['records']:
            if 'uploaded' not in record:
                record['uploaded'] = False
                modified_count += 1
        print(f"Added 'uploaded: false' to {modified_count} records")
    else:
        print("No 'records' key found in manifest")

    # Save the updated manifest
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Updated manifest saved to: {manifest_path}")


def main():
    """Main function to run the script."""
    # Define paths
    base_dir = Path(__file__).parent.parent.parent  # Go up to project root
    manifest_path = base_dir / "output" / "final_audio" / "manifest.json"
    backup_dir = base_dir / "output" / "final_audio" / "backups"

    print(f"Manifest path: {manifest_path}")
    print(f"Backup directory: {backup_dir}")

    # Check if manifest exists
    if not manifest_path.exists():
        print(f"Error: Manifest file not found at {manifest_path}")
        return

    # Create backup
    backup_path = create_backup(manifest_path, backup_dir)

    # Add uploaded field where missing
    add_uploaded_false_field(manifest_path)

    print("Script completed successfully!")


if __name__ == "__main__":
    main()