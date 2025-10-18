# Detailed Critical Issues - Code Locations and Fixes

## Issue #1: Resource Leak in AudioDownloader

### Location
- **File**: `src/downloader/audio_downloader.py`
- **Method**: `download_batch_async`
- **Lines**: 126-134

### Current Code
```python
semaphore = asyncio.Semaphore(self.config.max_concurrent_downloads)

async def download_with_semaphore(video: VideoMetadata) -> DownloadResult:
    async with semaphore:
        return await self.download_video_audio(video)

tasks = [download_with_semaphore(video) for video in videos]
results = await asyncio.gather(*tasks, return_exceptions=True)
```

### Problem
1. If a task raises an exception, it's caught by `return_exceptions=True`
2. Exceptions returned as results don't trigger cleanup
3. Temporary download files may not be cleaned up
4. Memory from DownloadResult objects not released if exception occurs

### Proposed Fix
```python
semaphore = asyncio.Semaphore(self.config.max_concurrent_downloads)

async def download_with_semaphore(video: VideoMetadata) -> DownloadResult:
    try:
        async with semaphore:
            return await self.download_video_audio(video)
    except Exception as e:
        # Ensure cleanup happens on exception
        self.output.warning(f"Download failed for {video.video_id}: {e}")
        return DownloadResult(
            video_id=video.video_id,
            success=False,
            error_message=str(e)
        )

tasks = [download_with_semaphore(video) for video in videos]
results = await asyncio.gather(*tasks)  # Remove return_exceptions since we handle it above
```

### Risk Assessment
- **Current Risk**: MEDIUM - Temp files accumulation, memory leaks under load
- **Impact**: Long-running crawler could exhaust disk space or memory
- **Frequency**: Triggered when batch downloads encounter errors

---

## Issue #2: Unsafe File Operations in FileManager.save_json

### Location
- **File**: `src/utils/file_manager.py`
- **Method**: `save_json`
- **Lines**: 153-197

### Current Code Analysis

**Problem 1**: Backup failure not critical
```python
if file_path.exists():
    self.create_backup(file_path)  # Returns on exception silently
```

**Problem 2**: Temp file orphaning
```python
except Exception as e:
    self.output.error(f"Failed to save JSON to {file_path}: {e}")
    # Clean up attempt is there but exception might prevent execution
    temp_file = file_path.with_suffix(file_path.suffix + '.tmp')
    if temp_file.exists():
        try:
            temp_file.unlink()
        except Exception:
            pass  # Silent failure - temp file remains
    return False
```

**Problem 3**: Race condition on file replacement
```python
# Between rename and return, file could be read/modified
temp_file.replace(file_path)
self.output.debug(f"Saved JSON atomically to {file_path}")
return True
```

### Proposed Fix
```python
def save_json(self, file_path: Path, data: Any, indent: int = 2) -> bool:
    """Save data to JSON file atomically with robust error handling."""
    temp_file = None
    try:
        # Ensure parent directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Create backup if file exists (non-critical)
        if file_path.exists():
            try:
                self.create_backup(file_path)
            except Exception as e:
                self.output.warning(f"Failed to create backup: {e} (continuing anyway)")

        # Convert data
        data = convert_numpy_types(data)

        # Write to temporary file
        temp_file = file_path.with_suffix(file_path.suffix + '.tmp')
        # Ensure temp file doesn't exist
        if temp_file.exists():
            temp_file.unlink()
            
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)

        # Atomic rename
        temp_file.replace(file_path)
        self.output.debug(f"Saved JSON atomically to {file_path}")
        return True
        
    except Exception as e:
        self.output.error(f"Failed to save JSON to {file_path}: {e}")
        # Ensure temp file cleanup
        if temp_file and temp_file.exists():
            try:
                temp_file.unlink()
                self.output.debug(f"Cleaned up temp file: {temp_file}")
            except Exception as cleanup_e:
                self.output.error(f"Failed to clean up temp file {temp_file}: {cleanup_e}")
        return False
```

### Risk Assessment
- **Current Risk**: MEDIUM - Could lead to stale temp files or corrupted saves
- **Impact**: Manifest corruption, disk space waste, recovery procedures needed
- **Frequency**: Every manifest save (dozens per run)

---

## Issue #3: Missing Exception Handling in Search Phase

### Location
- **File**: `src/crawler/search_phases.py`
- **Method**: `run_search_phase`
- **Lines**: 210-250

### Current Code Pattern
```python
# Check if it contains children's voice
if voice_result.is_child_voice:
    output.success(f"Children's voice detected...")
    
    # Add URLs somewhere here...
    with open(url_output_file, 'a', encoding='utf-8') as f:
        f.write(first_video.url + '\n')
    
    # Metadata additions might fail
    # Language detection might fail
    # Any failure leaves URL orphaned in file
```

### Problem
1. URLs added to file BEFORE validation complete
2. If language detection fails, URL remains in file
3. If metadata save fails, URL remains in file
4. Next run processes same URL again (duplication/wasted resources)

### Proposed Fix
```python
# Collect all data first
voice_result = voice_classifier.classify_audio_file(...)
if not voice_result.is_child_voice:
    continue

# Perform language detection
language_result = language_detector.detect_language(...) if language_detector else None

# Validate all operations succeeded before writing
if language_result is None or language_result.is_successful:
    # All validations passed, NOW write to files
    try:
        # Add URL
        with open(url_output_file, 'a', encoding='utf-8') as f:
            f.write(first_video.url + '\n')
        
        # Add metadata
        with open(metadata_output_file, 'a', encoding='utf-8') as f:
            metadata_list.append(first_video.to_dict())
            f.write(json.dumps(first_video.to_dict()) + '\n')
        
        output.success(f"Successfully added {first_video.video_id}")
    except Exception as e:
        output.error(f"Failed to write video data: {e}")
        # Rollback by removing from in-memory list
        if first_video.video_id in discovered_videos:
            del discovered_videos[first_video.video_id]
else:
    output.warning(f"Language detection failed for {first_video.video_id}, skipping")
```

### Risk Assessment
- **Current Risk**: HIGH - Data inconsistency, resource waste
- **Impact**: Duplicate processing, wasted API quota, incorrect final results
- **Frequency**: Every query with children's voice detected

---

## Issue #4: Incomplete Error Context

### Examples Found

#### Example 1: download_phases.py
```python
# ❌ BAD - Not enough context
except Exception as e:
    output.error(f"Failed to download audio for {video_id}: {e}")
    continue

# ✅ GOOD - Full context
except Exception as e:
    output.error(f"Failed to download audio for {video_id}")
    output.error(f"  Video details: title={video.title}, url={video.url}")
    output.error(f"  Attempted methods: {[a.method for a in result.attempts]}")
    output.error(f"  Last error: {result.error_message}")
    output.error(f"  Temp file path: {result.output_path}")
    output.debug(f"  Full exception: {e}")
    continue
```

#### Example 2: search_phases.py
```python
# ❌ BAD - Missing context
except Exception as e:
    output.error(f"Failed to initialize language detector: {e}")
    continue

# ✅ GOOD - Full context
except Exception as e:
    output.error(f"Failed to initialize language detector: {e}")
    output.error(f"  Config: enable_language_detection={getattr(config.analysis, 'enable_language_detection', 'unknown')}")
    output.error(f"  Recovery: Proceeding without language detection")
    output.warning(f"  This may affect filtering accuracy")
    language_detector = None
```

### Proposed Global Error Handler
```python
def log_error_with_context(output, error_type: str, error: Exception, context: dict):
    """Log error with full context for debugging."""
    output.error(f"{error_type}: {error}")
    output.error(f"  Exception type: {type(error).__name__}")
    output.error(f"  Traceback: {traceback.format_exc()}")
    for key, value in context.items():
        output.error(f"  {key}: {value}")
```

### Risk Assessment
- **Current Risk**: MEDIUM - Difficult debugging, slow issue resolution
- **Impact**: Longer MTTR (Mean Time To Resolution)
- **Frequency**: Every error condition

---

## Issue #5: Lock Timeout in ManifestManager

### Location
- **File**: `src/utils/file_manager.py`
- **Class**: `ManifestManager`
- **Method**: `acquire_lock`
- **Lines**: 348-361

### Current Code
```python
def acquire_lock(self) -> bool:
    """Acquire a lock on the manifest file."""
    start_time = time.time()
    while time.time() - start_time < self._lock_timeout:
        try:
            self._lock_file.touch(exist_ok=False)
            self.output.debug(f"Acquired manifest lock: {self._lock_file}")
            return True
        except FileExistsError:
            time.sleep(0.1)  # Fixed sleep, but leads to CPU thrashing
            continue
        except Exception as e:
            self.output.warning(f"Failed to acquire manifest lock: {e}")
            return False

    self.output.warning(f"Timeout acquiring manifest lock after {self._lock_timeout}s")
    return False
```

### Problems
1. **Fixed 0.1s sleep**: Under 10 parallel workers, lock will be attempted 100 times/sec
2. **No backoff**: Contention doesn't decrease over time
3. **Touch/exists pattern**: Not optimal for file locking, especially on network filesystems
4. **No retry accounting**: Doesn't track how many times it retried

### Proposed Fix
```python
def acquire_lock(self, max_retries: int = 300) -> bool:
    """Acquire a lock on the manifest file with exponential backoff."""
    import random
    
    retry_count = 0
    base_wait = 0.01  # 10ms
    max_wait = 1.0    # 1s
    
    while retry_count < max_retries:
        try:
            # Try to create lock file exclusively
            self._lock_file.touch(exist_ok=False)
            self.output.debug(f"Acquired manifest lock after {retry_count} retries: {self._lock_file}")
            return True
        except FileExistsError:
            # Calculate backoff with jitter
            wait_time = min(
                base_wait * (2 ** retry_count),  # Exponential backoff
                max_wait
            ) * (0.5 + random.random())  # Add jitter
            
            retry_count += 1
            if retry_count % 10 == 0:  # Log every 10 retries
                self.output.debug(f"Waiting for manifest lock (attempt {retry_count}/{max_retries})")
            
            time.sleep(wait_time)
            continue
        except Exception as e:
            self.output.warning(f"Failed to acquire manifest lock: {e}")
            return False

    self.output.warning(
        f"Timeout acquiring manifest lock after {retry_count} retries "
        f"({retry_count * base_wait:.2f}s+ elapsed)"
    )
    return False
```

### Risk Assessment
- **Current Risk**: MEDIUM - Lock contention under high concurrency
- **Impact**: Timeout failures, batch processing slowdown, incomplete operations
- **Frequency**: Every manifest access (very frequent)

### Recommended Monitoring
```python
# Add metrics tracking
self.lock_wait_time = 0
self.lock_acquire_attempts = 0
self.lock_timeouts = 0

# Then track:
self.lock_acquire_attempts += 1
self.lock_wait_time += retry_count * average_sleep_per_retry
if not acquired:
    self.lock_timeouts += 1

# Log metrics periodically
output.info(f"Lock stats: {self.lock_timeouts} timeouts, "
            f"avg wait {self.lock_wait_time/self.lock_acquire_attempts:.3f}s")
```

---

## Implementation Priority

### Phase 1 (Immediate - 1-2 days)
1. ✅ Issue #5: Fix lock timeout with exponential backoff
2. ✅ Issue #2: Add proper temp file cleanup
3. ✅ Issue #4: Add context to error messages (highest impact)

### Phase 2 (Near-term - 3-5 days)
1. Issue #3: Fix URL orphaning in search phase
2. Add integration tests for failure scenarios
3. Add monitoring/metrics

### Phase 3 (Medium-term - 1-2 weeks)
1. Issue #1: Refactor concurrent download handling
2. Add performance monitoring dashboard
3. Document recovery procedures

---

## Testing Checklist

- [ ] Lock contention test with 20 concurrent manifest writers
- [ ] Temp file cleanup verification after failed saves
- [ ] Search phase failure scenarios (network issues, classification errors)
- [ ] Concurrent async download failures
- [ ] Out-of-disk space handling
- [ ] Rapid start/stop cycle stability
- [ ] Memory leak detection under high concurrency
- [ ] Long-running stability test (24+ hours)

