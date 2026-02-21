# Contributing Guidelines

## Overview
This project follows conventional commit standards and encourages meaningful contributions with proper testing and documentation.

## Adding Features
1. Create feature branch: `git checkout -b feature/description`
2. Write code with type hints
3. Add tests for new functionality
4. Update documentation
5. Verify: `pytest --cov=src`

## Code Standards
- Follow PEP 8 style
- Use type hints
- Include docstrings
- Keep functions focused and testable

## Commit Format
- Use conventional commits: `feat:`, `fix:`, `docs:`, `test:`, `chore:`
- Example: `feat: add user authentication`
- Keep commits focused and atomic

## Pull Requests
- Describe changes clearly
- Reference related issues
- Ensure tests pass: `pytest`
- Request review from maintainers

## Testing
- Write tests for new code
- Maintain minimum 80% coverage
- Use mocks for external dependencies
- Run: `pytest --cov=src`

## Questions?
Open an issue or contact the maintainers.
