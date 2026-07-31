# Changelog

All notable changes to Lissn are documented here.
Versions follow [Semantic Versioning](https://semver.org/).

---

## [v0.7.0] – 2026-07-31

### ✏️ Inline Track Title Editing & Title Persistence

- **Single-line inline track title editing** — authenticated users can edit track titles directly within table rows by clicking the hover pencil icon or track title. Saves automatically on `Enter` or input blur.
- **SQLite title persistence** — manual title edits are saved in the `episodes` database table and preserved across library rescans and server restarts.
- **Track title reload/reindex button** — added a header control on show pages to reset all track titles back to their default `<subfolder>/<filename>` structure.
- **Rename validation & disambiguation** — prevents empty titles and handles duplicate track titles cleanly.

### 🧹 Automatic Audio Track Title Normalization

- **Cassette tape & side auto-renaming** — automatically detects and cleans digitized cassette naming patterns (e.g., `kass1sidea` -> `Kassett 1 side A`).
- **Book title prefix stripping** — automatically strips redundant show/book title prefixes from episode titles.
- **Track prefix normalization** — converts `trk` / `TRK` variants to standardized `Track`.
- **Delimiter cleanup** — converts `x`-delimited title strings (e.g. `01xMennxsom...`) into clean space-separated text.

### 🎵 Audio Player & Navigation Enhancements

- **Instant & robust track playback** — fixed track selection index accuracy, bottom player auto-reveal on show pages, and initial track preloading.
- **Playback control visibility** — audio player and play buttons are hidden for unauthenticated users and reveal automatically upon logging in.

### 🎨 UI & Layout Optimizations

- **Fixed table layout & ellipsis cropping** — applied `table-layout: fixed` and text ellipsis overflow to track tables to prevent horizontal overflow and inconsistent row heights on long titles.
- **Download button clipping fix** — optimized track table widths and column padding to ensure download buttons remain fully visible on all viewports.
- **Interactive footer links** — app name, version tag, and git commit ID in the footer are now clickable links pointing to the GitHub repository, release tag, and commit.
- **Header cleanup** — removed redundant top-banner GitHub button in favor of footer repository links.
- **Show card clean up** — removed redundant `by ` prefix on main page show cards.

### ⏱️ Performance & API Fixes

- **Rescan performance logging** — log elapsed media scanning duration per show type and total summary.
- **Scan API fix** — resolved `/api/scan` 500 error by excluding binary cover data from JSON responses.

---

## [v0.6.0] – 2026-07-30

### 🎵 Audio Player Reliability

- **Fixed audio player flakiness** — eliminated playback initialization issues and guaranteed rock-solid track playback across navigation transitions.

---

## [v0.5.3] – 2026-07-30

### 🎨 Desktop UI & Vertical Space Optimization

- **Upper-right show action buttons on desktop** — positioned the action button bar
  (`.detail-actions`) in the top-right corner of the show header box on viewports
  wider than 768px. This reclaims ~50–60px of vertical space previously used by the
  bottom button row and moves track listings up higher.

### 🎙️ Audio Book vs Podcast RSS Feed Differentiation

- **Serial vs Episodic feed types** — added `<itunes:type>serial</itunes:type>` for audio
  books and `<itunes:type>episodic</itunes:type>` for podcasts.
- **Sequential playback for Audio Books** — preserved natural chapter ordering in XML items
  and assigned `pubDate` timestamps so Chapter 1 receives the newest timestamp, ensuring
  podcast apps play audiobooks sequentially from start to finish.
- **Reverse chronological order for Podcasts** — newest podcast episodes are placed first at
  the top of the feed with the newest timestamp.

### 📜 Pretty-printed RSS XML

- **Formatted RSS XML output** — added 2-space XML indentation formatting via `ET.indent()`
  to `generate_rss_feed()`, making generated RSS feeds clean and easy to read.

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
