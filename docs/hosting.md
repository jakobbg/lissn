# Web Server Hosting & Reverse Proxy Guide

This guide details how to host **lissn** behind various web servers and reverse proxies for HTTPS termination, custom domain configuration, and secure remote access.

---

## 📋 Overview & Hosting Requirements

When hosting **lissn** in production:
- **Backend Service**: **lissn** runs locally by default on `http://127.0.0.1:8000` (or `0.0.0.0:8000`).
- **TLS/SSL Termination**: In production, place **lissn** behind a reverse proxy to handle HTTPS encryption, SSL certificate renewals, and standard HTTP (`80`) / HTTPS (`443`) port mapping.
- **HTTP Byte-Range Streaming**: **lissn** uses `HTTP 206 Partial Content` and `Accept-Ranges: bytes` headers to support seeking and scrubbing in media players. Reverse proxies must forward `Range` and `Content-Range` headers without stripping partial content responses.
- **Header Forwarding**: Ensure proxy headers (`Host`, `X-Real-IP`, `X-Forwarded-For`, `X-Forwarded-Proto`) are forwarded so podcast RSS feed URL generation and session cookies operate correctly.

---

## 🟢 Caddy (Recommended)

[Caddy](https://caddyserver.com/) provides automatic HTTPS certificate management via Let's Encrypt or ZeroSSL with minimal configuration.

### `Caddyfile` Configuration
```caddyfile
lissn.example.com {
    reverse_proxy localhost:8000
}
```

---

## 🔴 Apache HTTP Server

Apache HTTP Server (`httpd` / `apache2`) can proxy traffic to **lissn** using `mod_proxy` and `mod_proxy_http`.

### 1. Enable Required Apache Modules

- **Debian / Ubuntu**:
  ```bash
  sudo a2enmod proxy proxy_http ssl headers
  sudo systemctl restart apache2
  ```

- **RHEL / Fedora / CentOS**:
  Ensure `mod_proxy`, `mod_proxy_http`, `mod_ssl`, and `mod_headers` are loaded in `/etc/httpd/conf.modules.d/`.

- **FreeBSD**:
  Uncomment the following module lines in `/usr/local/etc/apache24/httpd.conf`:
  ```apache
  LoadModule proxy_module libexec/apache24/mod_proxy.so
  LoadModule proxy_http_module libexec/apache24/mod_proxy_http.so
  LoadModule ssl_module libexec/apache24/mod_ssl.so
  LoadModule headers_module libexec/apache24/mod_headers.so
  ```

### 2. VirtualHost Configuration

Create a virtual host configuration file (e.g. `/etc/apache2/sites-available/lissn.conf` on Linux or `/usr/local/etc/apache24/Includes/lissn.conf` on FreeBSD):

```apache
<VirtualHost *:80>
    ServerName lissn.example.com
    ServerAdmin webmaster@example.com

    # Redirect HTTP traffic to HTTPS
    RewriteEngine On
    RewriteCond %{HTTPS} off
    RewriteRule ^ https://%{HTTP_HOST}%{REQUEST_URI} [R=301,L]
</VirtualHost>

<VirtualHost *:443>
    ServerName lissn.example.com
    ServerAdmin webmaster@example.com

    # SSL / TLS Configuration
    SSLEngine on
    SSLCertificateFile /etc/letsencrypt/live/lissn.example.com/fullchain.pem
    SSLCertificateKeyFile /etc/letsencrypt/live/lissn.example.com/privkey.pem

    # Preserve original Host header for RSS feed URL generation
    ProxyPreserveHost On

    # Pass client protocol and real IP headers to lissn
    RequestHeader set X-Forwarded-Proto "https"
    RequestHeader set X-Forwarded-Port "443"

    # Reverse proxy directives
    ProxyPass / http://127.0.0.1:8000/
    ProxyPassReverse / http://127.0.0.1:8000/

    # Disable proxy response buffering to optimize byte-range audio streaming
    SetEnv force-proxy-request-1.0 1
    SetEnv proxy-nokeepalive 1

    # Logging
    ErrorLog ${APACHE_LOG_DIR}/lissn_error.log
    CustomLog ${APACHE_LOG_DIR}/lissn_access.log combined
</VirtualHost>
```

### 3. Enable Site & Reload Apache

- **Debian / Ubuntu**:
  ```bash
  sudo a2ensite lissn.conf
  sudo systemctl reload apache2
  ```

- **RHEL / CentOS**:
  ```bash
  sudo systemctl reload httpd
  ```

- **FreeBSD**:
  ```bash
  sudo service apache24 reload
  ```

---

## ⚡ Nginx

[Nginx](https://nginx.org/) is a high-performance reverse proxy and web server.

### Server Block Configuration

```nginx
server {
    listen 80;
    server_name lissn.example.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name lissn.example.com;

    ssl_certificate /etc/letsencrypt/live/lissn.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/lissn.example.com/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Disable proxy buffering for byte-range audio streaming
        proxy_buffering off;
    }
}
```

---

## 🔒 Tailscale Serve (Private Network)

For secure access across your private Tailscale mesh network without exposing ports to the public internet:

```bash
tailscale serve https / http://localhost:8000
```
