# Test reports directory
# This directory contains generated test reports from CI/CD pipeline

## Generated Files:
- `unit-tests.html` - Unit test results in HTML format
- `integration-tests.html` - Integration test results in HTML format
- `unit-tests.json` - Unit test results in JSON format
- `integration-tests.json` - Integration test results in JSON format
- `coverage/` - Code coverage reports

## Usage:
These reports are automatically generated during CI/CD pipeline execution and can be downloaded as artifacts from GitHub Actions.

## Local Testing:
To generate reports locally:
```bash
pytest tests/unit/ --html=reports/unit-tests.html --json-report --json-report-file=reports/unit-tests.json
pytest tests/integration/ --html=reports/integration-tests.html --json-report --json-report-file=reports/integration-tests.json
```
