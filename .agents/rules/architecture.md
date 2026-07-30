---
trigger: always_on
---

# Architecture & Platform Guidelines

* **Backend Stack**: All backend code must be written in Python (3.10+) using standard type hints.
* **Cross-Platform Support**: System design, dependencies, and file paths must natively support both FreeBSD and Linux.
* **API-First Approach**: Design backend logic around clean, decoupled API endpoints rather than tightly coupled monolithic views.
