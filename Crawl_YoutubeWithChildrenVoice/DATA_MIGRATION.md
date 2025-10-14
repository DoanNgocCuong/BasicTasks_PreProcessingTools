# Data Migration Guide

This guide explains how to migrate data from the old directory structure to the new modular architecture.

## Old vs New Directory Structure

### Old Structure (Monolithic System)

```
crawler_outputs/           # URL outputs and manifests
├── crawler_manifest.json  # Main manifest
├── crawler_manifest.backup_merge_20251008_225351.json  # Backup manifests
└── ...

final_audio_files/         # Final processed audio
├── manifest.json          # Audio manifest
├── manifest.backup_*.json # Backup manifests
└── audio_files/           # Actual audio files

youtube_audio_outputs/     # Downloaded audio files
└── *.mp3, *.wav files

youtube_url_outputs/       # URL output files
└── *.txt, *.json files
```

### New Structure (Modular System)

```
output/
├── url_outputs/           # URL output files and manifests
├── audio_outputs/         # Downloaded audio files
└── final_audio/           # Final processed audio files
    ├── manifest.json      # Main manifest
    └── manifest.backup_*.json  # Backup manifests
```

## Migration Steps

### 1. URL Outputs Migration

**From:** `crawler_outputs/` → **To:** `output/url_outputs/`

Files to migrate:

- `crawler_manifest.json` → `output/url_outputs/manifest.json`
- All `crawler_manifest.backup_*.json` → `output/url_outputs/manifest.backup_*.json`
- Any URL-related text/JSON files

### 2. Audio Downloads Migration

**From:** `youtube_audio_outputs/` → **To:** `output/audio_outputs/`

Files to migrate:

- All audio files (_.mp3, _.wav, etc.)

### 3. Final Audio Migration

**From:** `final_audio_files/` → **To:** `output/final_audio/`

Files to migrate:

- `manifest.json` → `output/final_audio/manifest.json`
- All `manifest.backup_*.json` → `output/final_audio/manifest.backup_*.json`
- Contents of `final_audio_files/audio_files/` → `output/final_audio/`

## Migration Script

Run the included migration script:

```bash
python migrate_data.py
```

This script will:

1. Create the new directory structure
2. Copy files to new locations
3. Update manifest paths if needed
4. Create backups of original directories
5. Validate migration success

## Post-Migration Verification

After migration, verify:

1. **Manifest files exist:**

   ```bash
   ls -la output/url_outputs/manifest.json
   ls -la output/final_audio/manifest.json
   ```

2. **Audio files are accessible:**

   ```bash
   ls -la output/audio_outputs/
   ls -la output/final_audio/
   ```

3. **Run system test:**
   ```bash
   python src/main.py --dry-run
   ```

## Rollback (if needed)

If migration fails, the original directories are preserved with `.backup` suffix:

```bash
# Restore from backup
mv crawler_outputs.backup crawler_outputs
mv final_audio_files.backup final_audio_files
mv youtube_audio_outputs.backup youtube_audio_outputs
mv youtube_url_outputs.backup youtube_url_outputs
```

## Configuration Updates

After migration, update any configuration files or scripts that reference the old paths:

- Update `.env` file if it contains hardcoded paths
- Update `crawler_config.json` if it references old directories
- Check any remaining scripts for path references

## Benefits of New Structure

1. **Cleaner Organization:** Related files grouped by function
2. **Modular Design:** Each component has its own output space
3. **Easier Maintenance:** Clear separation of concerns
4. **Future-Proof:** Extensible for new components
5. **Standard Layout:** Follows common project structures
