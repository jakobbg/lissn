---
trigger: always_on
---

# Frontend & UI Guidelines

* **Responsive Layouts**: UI must support both mobile and desktop screens with graceful fallbacks.
* **Theme Support**: Implement both Dark and Light modes. Auto-detect system preference via `prefers-color-scheme` with configurable manual switching persisted in `localStorage`.
* **Minimal JavaScript**: Keep client-side JS lean, vanilla, and accessible. Avoid heavy JS frameworks unless explicitly requested.
* **Accessibility**: Maintain semantic HTML, ARIA attributes, keyboard navigation, and proper contrast ratios.
* **Audio Player UX**: Support playback progress tracking and player state persistence using standard browser storage APIs (`localStorage`/`sessionStorage`).
