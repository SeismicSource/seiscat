# Seiscat Tests

This directory contains unit tests for the seiscat package.

## Running Tests

### Using unittest (built-in)

Run all tests:

```bash
python -m unittest discover tests
```

Run a specific test module:

```bash
python -m unittest tests.test_csv
```

Run a specific test class:

```bash
python -m unittest tests.test_csv.TestFieldMatchScore
```

Run a specific test method:

```bash
python -m unittest tests.test_csv.TestFieldMatchScore.test_perfect_match
```

Run with verbose output:

```bash
python -m unittest tests.test_csv -v
```

### Using pytest (requires installation)

Install pytest:

```bash
pip install pytest
```

Run all tests:

```bash
pytest tests/
```

Run with verbose output:

```bash
pytest tests/ -v
```

Run with coverage:

```bash
pip install pytest-cov
pytest tests/ --cov=seiscat --cov-report=html
```

## Test Coverage

### test_csv.py

Comprehensive unit tests for the CSV reader module (`seiscat/sources/csv.py`):

- **TestFieldMatchScore**: Tests field name matching logic
- **TestRemoveRedundantFields**: Tests redundant field removal
- **TestGuessFieldNames**: Tests automatic field name detection from CSV headers
- **TestCSVFileInfo**: Tests CSV file delimiter and row detection
- **TestReadOrigTimeFromYMDHMS**: Tests date-time parsing from separate components
- **TestSplitDateTime**: Tests date-time string splitting
- **TestNormalizeDateFormat**: Tests date format normalization (e.g., European to ISO)
- **TestReadOrigTimeFromDatetime**: Tests date-time parsing from combined fields
- **TestReadOrigTimeFromRow**: Tests date-time extraction from CSV rows
- **TestReadCSVRow**: Tests complete CSV row parsing into ObsPy Event objects
- **TestReadCSV**: Tests reading multiple rows into a Catalog
- **TestReadCatalogFromCSV**: Tests the main entry point with file handling and configuration

Total: 58 tests covering all functions in the CSV reader module.

## Adding New Tests

When adding new functionality to seiscat:

1. Create a new test file named `test_<module>.py` in the `tests/` directory
2. Import unittest and the module to test
3. Create test classes inheriting from `unittest.TestCase`
4. Name test methods starting with `test_`
5. Use assertions to verify expected behavior
6. Document tests with docstrings

Example:

```python
import unittest
from seiscat.module import function_to_test

class TestMyFunction(unittest.TestCase):
    """Test function_to_test."""

    def test_basic_functionality(self):
        """Test basic use case."""
        result = function_to_test('input')
        self.assertEqual(result, 'expected_output')
```

## Test Guidelines

- Each test should be independent and not rely on side effects from other tests
- Use `unittest.mock` for mocking external dependencies
- Use temporary files (`tempfile.NamedTemporaryFile`) for file-based tests
- Always clean up resources (use `try/finally` or context managers)
- Test both happy paths and edge cases
- Test error handling with `self.assertRaises()`
- Include docstrings describing what each test verifies
