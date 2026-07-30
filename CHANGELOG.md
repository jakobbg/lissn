# Changelog

All notable changes to Lissn are documented here.
Versions follow [Semantic Versioning](https://semver.org/).

---

## [v0.5.2] – 2026-07-30

### 🎙️ Subscribe Button & RSS UX

- **Removed redundant "Copy RSS" button** from the show detail page.
  The Subscribe button already falls back to copying the RSS URL to the
  clipboard when no podcast app handles the `podcast://` scheme, making
  a dedicated Copy RSS button unnecessary clutter.

- **Reliable Subscribe popover** replacing brittle direct `podcast://`
  scheme navigation: a small popover now offers the user both "Open in
  Podcast App" and "Copy RSS URL" actions, giving clear affordance on
  every platform.

- **Fixed podcast subscription URL scheme** — `podcast://` is used for
  HTTP feeds and `podcasts://` for HTTPS feeds, matching Apple Podcasts'
  expectations and preventing ATS / SSL failures on iOS.

- **Fixed Subscribe URL path prefix handling** — `get_subscribe_url()`
  now derives the full URL (including any custom subpath) from
  `config.base_url` rather than the raw `Host` header, fixing 404s on
  reverse-proxy deployments.

### 📱 Mobile & Navigation

- **Condensed mobile footer spacing** — reduced excess padding above and
  below the footer banner on small viewports.

- **Fixed Back to Library button** — scoped the CSS guard to
  `body:not(.show-page)` so the button is correctly hidden on the index
  page and visible on show pages regardless of whether the page was
  loaded directly or via SPA navigation.

- **SPA navigation body class sync** — `navigateTo()` now propagates
  `body.className` from the fetched document, ensuring CSS selectors
  that depend on `body.show-page` evaluate correctly after client-side
  route changes.

- **Mobile GitHub button styling** — added `.github-link-btn` to the
  mobile header icon-button rule so it renders as a uniform 38 × 38 px
  circular button alongside Sign In and Theme Toggle.

### 🎵 Episode Sorting

- **Folder-first natural sort** for all episode listings and RSS feeds.
  Episodes are now sorted by folder components first (e.g. Disc 1 before
  Disc 2), then by natural filename order within each folder (e.g.
  `Track 2.mp3` before `Track 10.mp3`).

### 🐛 Other Fixes

- **Multi-disc episode title prefix** fixed — subfolder path is stripped
  from track titles when constructing RSS `<title>` items to avoid
  double-prefixing.

- **iOS RSS pubDate ordering** corrected in generated feeds.

- **CSS `line-clamp` compatibility** — added standard `line-clamp`
  property alongside `-webkit-line-clamp` to silence deprecation
  warnings in modern browsers.

---

## [v0.5.1] – 2026-07-29

### Navigation & SPA Fixes

- Back to Library button scoped to show-detail pages via `body.show-page`
  class and CSS negation selector.
- SPA PJAX navigation correctly syncs `body.className` on route changes.
- GitHub link button styled uniformly on mobile viewports.

---

## [v0.5.0] – 2026-07-29

### New Features

- Lissn logo added across site header, show page, and README.
- Background SVG pattern overlay for page gradient backgrounds.
- Alt-click on a show opens it in a new tab/window.
- Paragraph spacing improvements in show descriptions.
- Audio player state persistence across browser reloads.
- Nested subfolder media playback fixed.

---

## [v0.4.1] – 2026-07-28

Minor bug fixes and stability improvements.

---

## [v0.4.0] – 2026-07-28

Initial public feature-complete release with podcast RSS feed support,
audiobook indexing, audio streaming with HTTP 206 byte-range support,
dark/light theme switching, and responsive mobile layout.

---

## [v0.3.0] – 2026-07-27

Podcast RSS feed conformance improvements and iTunes namespace support.

---

## [v0.2.0] – 2026-07-26

Authentication, session management, and show editing features.

---

## [v0.1.0] – 2026-07-25

Initial release.
