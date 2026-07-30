---
trigger: always_on
---

# Domain & Audio Media Guidelines

* **RSS Feed Standards**: All RSS feed endpoints must conform strictly to RSS 2.0 and iTunes podcast namespace specifications (including `<enclosure>`, `<itunes:duration>`, and `<itunes:explicit>`).
* **Unauthenticated Feed Access**: RSS feed XML endpoints and linked audio media files must be publicly accessible without requiring session authentication.
* **HTTP Byte-Range Streaming**: Audio streaming endpoints must support `HTTP 206 Partial Content` and `Accept-Ranges: bytes` headers to enable smooth seeking and scrubbing in media players.
