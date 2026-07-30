---
trigger: always_on
---

# Code Quality & Testing

* **Clean Code**: Code must be readable, clear, concise, and adhere to PEP 8 standards. Avoid over-engineering.
* **Automated Testing**: Create and maintain automated unit/integration tests (`pytest`) as part of feature implementation and bug fixes. All tests must reside in `tests/`.
* **Documentation**: Provide clear Python docstrings for modules, classes, and public functions.
* **Virtual Environment & Dependencies**: Declare dependencies in `pyproject.toml` and ensure code runs cleanly within `.venv`.
* **Security & Sanitization**: Sanitize user inputs and external RSS feed content before rendering in templates to prevent XSS vulnerabilities.
