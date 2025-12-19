# Contributing to SmartSpend

Thank you for your interest in contributing to SmartSpend! This document provides guidelines and instructions for contributing.

## Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Focus on what is best for the community
- Show empathy towards other community members

## How to Contribute

### Reporting Bugs

Before creating bug reports, please check existing issues. When creating a bug report, include:

- **Clear title and description**
- **Steps to reproduce**
- **Expected vs actual behavior**
- **Screenshots** (if applicable)
- **Environment details** (OS, Python version, browser)
- **Sample CSV** (if related to CSV parsing)

**Bug Report Template:**
```markdown
## Bug Description
[Clear description of the bug]

## Steps to Reproduce
1. Go to '...'
2. Click on '...'
3. Upload file '...'
4. See error

## Expected Behavior
[What you expected to happen]

## Actual Behavior
[What actually happened]

## Environment
- OS: [e.g., Windows 11]
- Python: [e.g., 3.11.5]
- Browser: [e.g., Chrome 120]

## Additional Context
[Any other relevant information]
```

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, include:

- **Clear title and description**
- **Use case** (why is this needed?)
- **Proposed solution**
- **Alternatives considered**
- **Additional context**

### Pull Requests

1. **Fork the repository**
2. **Create a feature branch** (`git checkout -b feature/amazing-feature`)
3. **Make your changes**
4. **Test thoroughly**
5. **Commit with clear messages**
6. **Push to your fork**
7. **Open a Pull Request**

**PR Guidelines:**
- Link to related issue
- Describe changes clearly
- Include tests if applicable
- Update documentation
- Follow code style guidelines

## Development Setup

### Prerequisites
- Python 3.11+
- Git
- pip

### Local Setup

1. **Clone your fork:**
```bash
git clone https://github.com/YOUR_USERNAME/smartspend.git
cd smartspend
```

2. **Create virtual environment:**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
pip install -r viewer/requirements.txt
```

4. **Run backend:**
```bash
python api/app.py
```

5. **Run frontend (new terminal):**
```bash
streamlit run viewer/app.py
```

## Code Style Guidelines

### Python

Follow [PEP 8](https://pep8.org/) style guide:

- **Indentation:** 4 spaces
- **Line length:** 100 characters max
- **Naming:**
  - Functions/variables: `snake_case`
  - Classes: `PascalCase`
  - Constants: `UPPER_SNAKE_CASE`

**Example:**
```python
def detect_date_column(columns):
    """
    Detect date column from CSV headers.
    
    Args:
        columns: List of column names
        
    Returns:
        str: Detected date column name
        
    Raises:
        ValueError: If no date column found
    """
    DATE_ALIASES = ['date', 'transaction_date', 'txn_date']
    # Implementation...
```

### Documentation

- **Docstrings:** Use Google style
- **Comments:** Explain why, not what
- **README:** Update if adding features
- **API docs:** Update if changing endpoints

### Git Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting)
- `refactor`: Code refactoring
- `test`: Adding/updating tests
- `chore`: Maintenance tasks

**Examples:**
```
feat(csv): Add support for Excel files

- Add openpyxl dependency
- Implement Excel parser
- Update upload endpoint

Closes #123
```

```
fix(api): Handle whitespace in amount columns

Previously, empty cells with whitespace caused parsing to fail.
Now treats whitespace as empty value.

Fixes #456
```

## Testing

### Running Tests

```bash
# Test CSV auto-mapper
python test_csv_formats.py

# Diagnose specific CSV
python diagnose_csv.py sample.csv
```

### Adding Tests

When adding features, include tests:

1. **Add test CSV** to `test_data/`
2. **Add test case** to `test_csv_formats.py`
3. **Run tests** to verify

**Test Case Template:**
```python
{
    "name": "Your Format Name",
    "file": "test_data/your_test.csv",
    "expected_transactions": 10,
    "expected_pattern": "Debit/Credit"
}
```

## Project Structure

```
smartspend/
├── api/                    # Backend API
│   └── app.py             # Flask application
├── core/                   # Business logic
│   ├── loader.py          # CSV auto-mapper
│   ├── subscriptions.py   # Subscription detection
│   └── overspending.py    # Overspending analysis
├── viewer/                 # Frontend UI
│   └── app.py             # Streamlit application
├── docs/                   # Documentation
│   ├── ARCHITECTURE.md    # System design
│   ├── API.md             # API reference
│   └── DEPLOYMENT.md      # Deployment guide
├── test_data/              # Test CSV files
└── requirements.txt        # Dependencies
```

## Adding Support for New CSV Formats

### Step 1: Identify Pattern

Analyze the CSV structure:
- What are the column names?
- How are amounts represented?
- What date format is used?

### Step 2: Add Column Aliases

Edit `core/loader.py`:

```python
def detect_date_column(columns):
    aliases = [
        'date', 
        'transaction_date',
        'your_new_alias'  # Add here
    ]
    # ...
```

### Step 3: Create Test CSV

Add to `test_data/`:
```csv
Your Date Column,Your Description,Your Amount
01/01/2024,Transaction 1,100.00
02/01/2024,Transaction 2,200.00
```

### Step 4: Add Test Case

In `test_csv_formats.py`:
```python
{
    "name": "Your Bank Format",
    "file": "test_data/your_bank.csv",
    "expected_transactions": 2,
    "expected_pattern": "Signed Amount"
}
```

### Step 5: Test

```bash
python test_csv_formats.py
```

### Step 6: Document

Update `README.md` with new supported format.

## Areas for Contribution

### High Priority

- [ ] Support for Excel files (`.xlsx`)
- [ ] Currency symbol handling (₹, $, €)
- [ ] Thousand separator support (1,000.00)
- [ ] More date format variations
- [ ] Rate limiting on API endpoints

### Medium Priority

- [ ] Manual column mapping UI
- [ ] CSV validation before upload
- [ ] Export analytics to PDF
- [ ] Multi-file upload (combine statements)
- [ ] Spending category classification

### Low Priority

- [ ] Dark mode for UI
- [ ] Customizable date ranges
- [ ] Budget recommendations
- [ ] Email alerts for overspending
- [ ] Mobile-responsive design improvements

## Review Process

### For Contributors

1. **Self-review** your code
2. **Test thoroughly**
3. **Update documentation**
4. **Submit PR** with clear description

### For Reviewers

1. **Check functionality** (does it work?)
2. **Review code quality** (is it maintainable?)
3. **Verify tests** (are they comprehensive?)
4. **Check documentation** (is it updated?)
5. **Provide constructive feedback**

## Release Process

### Versioning

We use [Semantic Versioning](https://semver.org/):
- **MAJOR:** Breaking changes
- **MINOR:** New features (backward compatible)
- **PATCH:** Bug fixes

### Release Checklist

- [ ] Update version in `README.md`
- [ ] Update `CHANGELOG.md`
- [ ] Tag release in Git
- [ ] Deploy to production
- [ ] Announce in discussions

## Getting Help

- **Questions:** Open a discussion on GitHub
- **Bugs:** Create an issue
- **Security:** Email maintainers directly
- **Chat:** Join our community (if available)

## Recognition

Contributors will be recognized in:
- `README.md` acknowledgments
- Release notes
- GitHub contributors page

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

**Thank you for contributing to SmartSpend!** 🎉

Your contributions help make financial analytics accessible and privacy-focused for everyone.
