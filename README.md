# WarThunderCopilot
A Second pilot for WarThunder Air-Sim-Battles

## Development

### Running Tests

This project includes comprehensive unit tests to ensure code quality and functionality. The tests are built using pytest.

#### Install Dependencies

```bash
pip install -r requirements.txt
```

#### Run All Tests

```bash
pytest tests/ -v
```

#### Run Tests with Coverage

```bash
pytest tests/ --cov=code --cov-report=term --cov-report=html
```

This will generate a coverage report in the terminal and create an HTML coverage report in the `htmlcov/` directory.

#### Run Specific Test Files

```bash
# Test backend settings module
pytest tests/test_settings.py -v

# Test backend warning engine
pytest tests/test_warningengine.py -v

# Test backend sound engine
pytest tests/test_soundengine.py -v

# Test backend telemetry fetcher
pytest tests/test_wtfetcher.py -v
```

### Continuous Integration

Tests are automatically run on every push to the `main` and `Release_Candidate` branches, as well as on pull requests. The build workflows will only proceed if all tests pass successfully.

- **Test Workflow**: Runs all unit tests and generates coverage reports
- **Build Workflows**: Run tests before building the application executable
