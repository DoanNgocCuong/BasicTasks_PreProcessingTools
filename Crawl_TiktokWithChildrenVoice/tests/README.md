# TikTok Children's Voice Crawler - Test Scripts

This directory contains test scripts for validating the TikTok crawler functionality.

## Test Scripts

### `test_exhaustive_pagination.py`

- **Purpose**: Tests the exhaustive pagination functionality to ensure ALL available results are extracted
- **Features**:
  - Limited exhaustive search (max 100 videos)
  - Single page comparison
  - Unlimited exhaustive search (gets all available results)
- **Key Validation**: Verifies that the crawler uses API's `has_more` and `next_cursor` values correctly
- **Expected Result**: Should extract significantly more videos than single API calls

### `test_keyword_search.py`

- **Purpose**: Tests basic keyword search functionality
- **Features**: Validates Vietnamese keyword search with proper UTF-8 encoding
- **Key Validation**: Ensures keywords are properly encoded and API responses are handled correctly

### `test_system.py`

- **Purpose**: General system integration tests
- **Features**: Tests overall crawler configuration and component integration
- **Key Validation**: Ensures all components work together properly

## Running Tests

From the main crawler directory:

```bash
# Run individual tests
python tests/test_exhaustive_pagination.py
python tests/test_keyword_search.py
python tests/test_system.py

# Or from the tests directory
cd tests
python test_exhaustive_pagination.py
python test_keyword_search.py
python test_system.py
```

## Test Environment

- Requires active `.env` file with TikTok API credentials
- Uses the same configuration as the main crawler
- Respects API rate limits with appropriate delays
