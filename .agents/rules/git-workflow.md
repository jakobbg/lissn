---
trigger: always_on
---

# Git Workflow & Release Management

* **Detailed Commit Explanations Mandatory**: Every git commit must include comprehensive, detailed explanations in the commit body/details detailing:
  - **What** changes were made.
  - **Why** the changes were made (motivation and context).
  - **Technical rationale** and implementation details.
  - Clear emojis for visual organization and clarity.
* **Versioning & Releases**: Begin project versioning at `v0.1`. Create GitHub releases via the installed `gh` CLI whenever requested. Release notes must be verbose and detailed, created by inspecting all commits and associated commit comments/details since the previous release.
