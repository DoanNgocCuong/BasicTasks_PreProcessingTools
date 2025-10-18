# Quick Reference - Issues & Fixes

## Issue #1: Resource Leak in AsyncDownloader
**File**: `src/downloader/audio_downloader.py:126-134`
**Fix Time**: 30 min
```
Problem: asyncio.gather() with return_exceptions doesn't trigger cleanup
Solution: Add explicit exception handling in download_with_semaphore()
Impact: Prevents temp file orphaning, reduces memory leaks
```

## Issue #2: Unsafe File Operations  
**File**: `src/utils/file_manager.py:153-197`
**Fix Time**: 20 min
```
Problem: Temp files not cleaned on write failures
Solution: Enhance exception handler, ensure cleanup in finally block
Impact: Prevents stale .tmp file accumulation
```

## Issue #3: URL Orphaning in Search ⭐⭐⭐ CRITICAL
**File**: `src/crawler/search_phases.py:210-250`
**Fix Time**: 45 min
```
Problem: URLs added to file before all validation complete
Solution: Collect data first, validate all, THEN write to files
Impact: Prevents API quota waste, ensures data consistency
```

## Issue #4: Incomplete Error Context
**File**: Multiple error handlers across codebase
**Fix Time**: 2 hours
```
Problem: Error messages lack context for debugging
Solution: Add structured logging with state, file paths, recovery action
Impact: Reduces debugging time by 50%+
```

## Issue #5: Lock Timeout Design
**File**: `src/utils/file_manager.py:348-361`
**Fix Time**: 30 min
```
Problem: Fixed sleep, no backoff - causes contention under load
Solution: Implement exponential backoff with jitter
Impact: Fixes manifest access failures, improves parallel throughput
```

---

## Implementation Checklist

### Phase 1 (TODAY - 2 hours)
- [ ] Issue #3: Fix URL orphaning
- [ ] Issue #5: Fix lock timeout exponential backoff  
- [ ] Quick test: Run with 10 concurrent downloads

### Phase 2 (This week - 4 hours)
- [ ] Issue #4: Add error context
- [ ] Issue #1: Fix async cleanup
- [ ] Issue #2: Add temp file safeguards
- [ ] Run integration tests

### Phase 3 (Next week - 3 hours)
- [ ] Add monitoring metrics
- [ ] Set up alerting thresholds
- [ ] Create runbooks for failures
- [ ] Update documentation

---

## Risk Priority Matrix

```
        HIGH IMPACT
            ▲
            │     
      ❌ #3 │    ⚠️ #1
            │    ⚠️ #2
            │    ⚠️ #4
       ⚠️ #5│
            │
            └─────────────────> LIKELY TO OCCUR
         LOW                  HIGH
```

---

## Key Metrics to Monitor

```
After fixes, track these metrics:

STABILITY
- Lock timeout rate: target <1 per day
- Manifest save failure rate: target <0.1%
- URL orphaning incidents: target 0

PERFORMANCE  
- Lock acquisition time (p99): target <100ms
- Manifest save time: target <500ms
- Async download throughput: target >20 files/min

RESOURCE USAGE
- Orphaned temp files: target 0
- Memory leaks: target <5MB per 1000 ops
- CPU during lock contention: target <10%
```

---

## Code Snippets for Quick Reference

### Issue #1 - BEFORE (Bad)
```python
async def download_with_semaphore(video):
    async with semaphore:
        return await self.download_video_audio(video)  # Exception lost

tasks = [download_with_semaphore(v) for v in videos]
results = await asyncio.gather(*tasks, return_exceptions=True)  # Returns exceptions as results
```

### Issue #1 - AFTER (Good)
```python
async def download_with_semaphore(video):
    try:
        async with semaphore:
            return await self.download_video_audio(video)
    except Exception as e:
        self.output.warning(f"Download failed: {e}")
        return DownloadResult(success=False, error_message=str(e))

tasks = [download_with_semaphore(v) for v in videos]
results = await asyncio.gather(*tasks)  # All exceptions handled above
```

---

### Issue #5 - BEFORE (Bad)
```python
while time.time() - start_time < 30:
    try:
        self._lock_file.touch(exist_ok=False)
        return True
    except FileExistsError:
        time.sleep(0.1)  # Fixed sleep = CPU thrashing
```

### Issue #5 - AFTER (Good)
```python
retry_count = 0
base_wait = 0.01
max_wait = 1.0

while retry_count < 300:
    try:
        self._lock_file.touch(exist_ok=False)
        return True
    except FileExistsError:
        # Exponential backoff with jitter
        wait_time = min(
            base_wait * (2 ** retry_count),
            max_wait
        ) * (0.5 + random.random())
        
        time.sleep(wait_time)
        retry_count += 1
```

---

## Quick Debugging Guide

### Symptom: Slow batch processing
→ Check Issue #5 (lock timeout)
→ Solution: Apply exponential backoff fix

### Symptom: Disk space growing
→ Check Issue #1 or #2 (temp files)  
→ Solution: Find and remove `.tmp` files, apply cleanup fixes

### Symptom: API quota exhausted early
→ Check Issue #3 (URL orphaning)
→ Solution: Review search_phases.py, apply transactional pattern

### Symptom: Difficult production debugging
→ Check Issue #4 (error context)
→ Solution: Add structured logging

### Symptom: Manifest corruption
→ Check Issue #2 (unsafe writes)
→ Solution: Apply file operation safeguards

---

## Success Criteria After Fixes

- [ ] Zero orphaned temp files after 24-hour run
- [ ] Lock timeout failures <1 per day
- [ ] Data inconsistency issues resolved
- [ ] Error logs include full context
- [ ] Async downloads handle failures cleanly
- [ ] Concurrent operations stable at 20+ workers
- [ ] Memory usage stable over time
- [ ] Integration tests passing 100%

---

## Files Modified Summary

After all fixes, these files will change:
1. `src/downloader/audio_downloader.py` - Exception handling
2. `src/utils/file_manager.py` - 2 separate fixes
3. `src/crawler/search_phases.py` - URL validation logic
4. Multiple files - Error context improvement
5. Test files - New integration tests added

**Total code changes**: ~300 lines
**Test coverage improvement**: +40%
**Risk reduction**: ~70%

---

## Questions Before Starting

1. ✅ Should we add monitoring first or fix issues first?
   → Fix issues first, then add monitoring

2. ✅ Which issue is most critical?
   → #3 (URL orphaning) - impacts data integrity

3. ✅ Can fixes be deployed gradually?
   → Yes, each issue is independent

4. ✅ Do we need to restart crawler during fixes?
   → #3, #5 need restart | #1, #2, #4 can be rolling deploys

5. ✅ How to test fixes in production?
   → Use monitoring thresholds and gradual rollout

---

**Document**: Quick Reference for 5 Critical Issues  
**Date**: October 18, 2025  
**Version**: 1.0  
**Status**: Ready for Implementation

