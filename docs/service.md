# Running lissn as a Service (FreeBSD & Linux)

This guide details how to run **lissn** as a background service daemon on **FreeBSD** (via `rc.d`) and **Linux** (via `systemd`), including log file management and rotation.

---

## 🛠️ Prerequisites & Setup

Before installing the service definition:

1. **Dedicated User Account**: It is strongly recommended to run **lissn** under an unprivileged user (e.g. `lissn`).
   - **Linux**: `sudo useradd -r -s /bin/false lissn`
   - **FreeBSD**: `sudo pw useradd lissn -d /usr/local/www/lissn -s /usr/sbin/nologin -c "lissn daemon"`

2. **Directory Permissions**: Ensure the user owns the application folder and media directories:
   ```bash
   sudo chown -R lissn:lissn /usr/local/www/lissn
   ```

3. **Virtual Environment**: Initialize `.venv` and install dependencies:
   ```bash
   cd /usr/local/www/lissn
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -e .
   ```

---

## 🐧 Linux (`systemd`) Installation

### 1. Copy Service File
Copy the template service unit from `scripts/service/lissn.service` to `/etc/systemd/system/lissn.service`:

```bash
sudo cp scripts/service/lissn.service /etc/systemd/system/lissn.service
```

### 2. Configure Service Unit
If your installation path differs from `/usr/local/www/lissn` or your service user is different, edit `/etc/systemd/system/lissn.service`:

```ini
[Unit]
Description=lissn - Audiobooks and Podcasts Indexer & RSS Server
After=network.target network-online.target
Wants=network-online.target

[Service]
Type=simple
User=lissn
Group=lissn
WorkingDirectory=/usr/local/www/lissn
Environment="PATH=/usr/local/www/lissn/.venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/usr/local/www/lissn/.venv/bin/python3 -m lissn.app
Restart=on-failure
RestartSec=5s

StandardOutput=append:/usr/local/www/lissn/logs/lissn.log
StandardError=append:/usr/local/www/lissn/logs/lissn_error.log

ProtectSystem=full
ProtectHome=read-only
PrivateTmp=true
NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
```

### 3. Enable & Start Service
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now lissn
```

### 4. Manage & Monitor
- **Check Status**: `sudo systemctl status lissn`
- **Restart Service**: `sudo systemctl restart lissn`
- **View Logs**: `tail -f /usr/local/www/lissn/logs/lissn.log` or `journalctl -u lissn -f`

---

## 😈 FreeBSD (`rc.d`) Installation

### 1. Copy `rc.d` Script
Copy `scripts/service/lissn` to `/usr/local/etc/rc.d/lissn` and make it executable:

```bash
sudo cp scripts/service/lissn /usr/local/etc/rc.d/lissn
sudo chmod +x /usr/local/etc/rc.d/lissn
```

### 2. Configure `/etc/rc.conf`
Enable the service and customize settings in `/etc/rc.conf`:

```sh
# Enable lissn service
lissn_enable="YES"
lissn_user="lissn"
lissn_dir="/usr/local/www/lissn"
```

Optional settings available in `/etc/rc.conf`:
- `lissn_python`: Path to Python executable (default: `${lissn_dir}/.venv/bin/python3`).
- `lissn_log`: Custom log file path (default: `${lissn_dir}/logs/lissn.log`).

### 3. Start & Manage Service
- **Start**: `sudo service lissn start`
- **Stop**: `sudo service lissn stop`
- **Restart**: `sudo service lissn restart`
- **Status**: `sudo service lissn status`

---

## 🪵 Log Management & Rotation

**lissn** outputs log entries to `logs/lissn.log` (which is gitignored).

### Verbose & Debug Logging
By default, **lissn** logs at `INFO` level. To enable verbose `DEBUG` logging for troubleshooting:
- **Environment Variable**: `export LISSN_VERBOSE=true`
- **Systemd**: Uncomment `Environment="LISSN_VERBOSE=true"` in `/etc/systemd/system/lissn.service`.
- **FreeBSD rc.conf**: Set `lissn_verbose="YES"` in `/etc/rc.conf`.
- **Config file (`config/lissn.json`)**: Add `"verbose": true`.


### Linux (`logrotate`)

Create `/etc/logrotate.d/lissn`:

```text
/usr/local/www/lissn/logs/*.log {
    weekly
    missingok
    rotate 4
    compress
    delaycompress
    notifempty
    create 0640 lissn lissn
}
```

### FreeBSD (`newsyslog`)
Create `/usr/local/etc/newsyslog.conf.d/lissn.conf`:

```text
# logfilename                         [owner:group]  mode count size when  flags [/pid_file] [sig_num]
/usr/local/www/lissn/logs/lissn.log   lissn:lissn    640  5     1000 *     JC    /var/run/lissn.pid
```
