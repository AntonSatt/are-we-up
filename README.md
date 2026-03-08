# are-we-up

<p align="center">
  <img src="assets/are-we-up.png" alt="Uptime Overview Dashboard" width="600">
</p>

Self-hostable uptime monitoring stack. Define your targets in one YAML file, run `docker compose up`, and get dashboards with alerting out of the box.

Built on Prometheus + Grafana + Alertmanager + Blackbox Exporter.

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/youruser/are-we-up.git
cd are-we-up

# 2. Create your .env file (optional — only needed for alerting)
cp .env.example .env
# Edit .env with your notification credentials

# 3. Add your targets
# Edit targets.yml — add the sites and services you want to monitor

# 4. Start the stack
docker compose up -d
```

Open [http://localhost:3000](http://localhost:3000) for Grafana (default login: `admin`/`admin`).

## Services

| Service           | Port  | URL                           |
|-------------------|-------|-------------------------------|
| Grafana           | 3000  | http://localhost:3000         |
| Prometheus        | 9090  | http://localhost:9090         |
| Alertmanager      | 9093  | http://localhost:9093         |
| Blackbox Exporter | 9115  | http://localhost:9115         |
| Node Exporter     | 9100  | http://localhost:9100/metrics |
| cAdvisor          | 8080  | http://localhost:8080         |

All ports are configurable via `.env`.

## Configuration Files

There are two files you edit to tell are-we-up what to monitor:

- **`targets.yml`** — websites and services to check (HTTP, TCP, ping). These are monitored from your are-we-up server — no agent needed on the remote side.
- **`agents.json`** — remote servers where you've installed the [remote agent](#multi-server-monitoring) to get system metrics (CPU, memory, disk). See [Multi-Server Monitoring](#multi-server-monitoring) for setup instructions.

Both files are picked up automatically within 30 seconds — no restart needed.

## Adding Targets

Edit `targets.yml` to add or remove monitoring targets.

### HTTP/HTTPS Sites

```yaml
- targets:
    - https://your-site.com
  labels:
    name: your-site
    module: http_2xx
```

### TCP Services

```yaml
- targets:
    - your-db-host:5432
  labels:
    name: postgres
    module: tcp_connect
```

### ICMP Ping

```yaml
- targets:
    - 8.8.8.8
  labels:
    name: google-dns
    module: icmp
```

### Available Modules

| Module           | Description                              |
|------------------|------------------------------------------|
| `http_2xx`       | HTTPS probe with TLS validation          |
| `http_2xx_no_tls`| HTTP probe, skips TLS verification       |
| `tcp_connect`    | TCP connection check                     |
| `icmp`           | ICMP ping (requires container privileges)|

## Dashboards

Five pre-built dashboards are provisioned automatically:

- **Uptime Overview** — all targets at a glance: status, response time, uptime history, SSL cert expiry
- **Site Detail** — per-site deep-dive with response time breakdown (DNS, TCP, TLS, processing, transfer), status code history, SSL countdown
- **System Overview** — CPU, memory, disk, network from Node Exporter
- **Docker Containers** — per-container CPU, memory, network, disk I/O with summary table
- **Stack Health** — Prometheus self-monitoring: scrape targets, memory, storage, query performance, alert status

## Alerting

Alerts are pre-configured and fire when:

| Alert                  | Condition                                  | Severity |
|------------------------|--------------------------------------------|----------|
| TargetDown             | Probe fails for 2 minutes                  | critical |
| HighResponseTime       | Response > 3s for 5 minutes                | warning  |
| SSLCertExpiringSoon    | SSL cert expires in < 14 days              | warning  |
| SSLCertExpiryCritical  | SSL cert expires in < 3 days               | critical |
| HTTPStatusCodeChange   | Non-200 response for 5 minutes             | warning  |
| HighCPUUsage           | CPU > 85% for 10 minutes                   | warning  |
| HighMemoryUsage        | Memory > 85% for 10 minutes                | warning  |
| DiskSpaceLow           | Disk > 85% full for 10 minutes             | warning  |
| DiskSpaceCritical      | Disk > 95% full for 5 minutes              | critical |
| PrometheusTargetMissing| Scrape target down for 5 minutes           | warning  |

### Notification Channels

Configure in `.env`:

**Discord** — set `DISCORD_WEBHOOK_URL`

**Slack** — set `SLACK_WEBHOOK_URL` and optionally `SLACK_CHANNEL`

**Email** — set `SMTP_SMARTHOST`, `SMTP_FROM`, `SMTP_AUTH_USERNAME`, `SMTP_AUTH_PASSWORD`, and `ALERT_EMAIL_TO`

**Generic Webhook** — set `GENERIC_WEBHOOK_URL` (receives Alertmanager webhook payloads)

Unconfigured channels are silently skipped (they'll fail to deliver but won't block other receivers).

## Multi-Server Monitoring

By default, are-we-up only collects system metrics (CPU, memory, disk) from the machine it runs on. To monitor remote servers (like a VPS on DigitalOcean, Oracle Cloud, Hetzner, etc.), you install a small agent on each one.

> **Note:** This is only needed for system metrics. Uptime/HTTP monitoring works without any agent — just add URLs to `targets.yml`.

### How it works

Your monitoring server needs to pull data from your remote servers. To do this securely, you:

1. Run a small metrics collector (Node Exporter) on the remote server
2. Open one port (9100) on the remote server, but **only** for your monitoring server's IP — everyone else is blocked
3. Tell Prometheus where to find the remote server

### What you need

- **Remote server:** Ubuntu 22.04 or 24.04 with Docker installed
- **Your public IP:** This is the IP of the network where are-we-up runs (your home network if you run it on a Raspberry Pi, for example). Find it by running `curl -s ifconfig.me` on that machine.

### Step 1 — Set up the remote server

Copy the `remote-agent` folder to your remote server and run the setup script:

```bash
scp -r remote-agent/ user@your-server:~/are-we-up-agent

ssh user@your-server
cd ~/are-we-up-agent
bash setup.sh
```

This starts Node Exporter. It only listens on localhost — nobody can reach it from the outside yet.

### Step 2 — Allow your monitoring server through the firewall

On the remote server, allow **only your IP** to access the metrics port:

```bash
# Replace with the public IP of the machine running are-we-up
sudo ufw allow from YOUR_PUBLIC_IP to any port 9100 proto tcp
```

For example, if your home IP is `80.216.96.11`:

```bash
sudo ufw allow from 80.216.96.11 to any port 9100 proto tcp
```

Now only that one IP can reach port 9100. Everyone else is blocked.

### Step 3 — Tell Prometheus about the remote server

On your monitoring server, add the remote server to `agents.json`:

```json
[
  {
    "targets": ["node-exporter:9100"],
    "labels": { "name": "local" }
  },
  {
    "targets": ["143.47.100.25:9100"],
    "labels": { "name": "oracle-server" }
  }
]
```

Prometheus picks up the change automatically within 30 seconds — no restart needed.

The remote server should appear in your dashboards shortly after.

### Adding more servers

Repeat steps 1-2 on each remote server, then add them to `agents.json`:

```json
[
  {
    "targets": ["node-exporter:9100"],
    "labels": { "name": "local" }
  },
  {
    "targets": ["143.47.100.25:9100"],
    "labels": { "name": "oracle-server" }
  },
  {
    "targets": ["164.92.200.50:9100"],
    "labels": { "name": "digitalocean-1" }
  },
  {
    "targets": ["129.151.60.10:9100"],
    "labels": { "name": "hetzner-web" }
  }
]
```

### If your IP changes

Most home internet connections have a dynamic IP that can change from time to time. If it changes, the firewall on your remote servers will block the new IP and metrics will stop flowing.

You'll notice because the dashboards will stop updating for those servers. To fix it, SSH into each remote server and update the firewall rule:

```bash
# Remove the old rule
sudo ufw delete allow from OLD_IP to any port 9100 proto tcp

# Add the new one
sudo ufw allow from NEW_IP to any port 9100 proto tcp
```

> **Tip:** Some ISPs offer a static IP (one that never changes) for a small monthly fee. If you monitor several servers, it might be worth asking your ISP about it.

### Security

- Node Exporter has no built-in authentication, which is why the firewall rule is important — it ensures only your monitoring server can read the data.
- The docker-compose binds to `127.0.0.1:9100` so the port is not directly exposed. The firewall rule is what lets your monitoring server through.
- Never open port 9100 to everyone (`ufw allow 9100` without a `from` IP). Always restrict it to your monitoring server's IP.

## Configuration Reference

### Environment Variables

| Variable              | Default             | Description                    |
|-----------------------|---------------------|--------------------------------|
| `PROMETHEUS_PORT`     | 9090                | Prometheus UI port             |
| `GRAFANA_PORT`        | 3000                | Grafana UI port                |
| `ALERTMANAGER_PORT`   | 9093                | Alertmanager UI port           |
| `BLACKBOX_PORT`       | 9115                | Blackbox Exporter port         |
| `NODE_EXPORTER_PORT`  | 9100                | Node Exporter port             |
| `CADVISOR_PORT`       | 8080                | cAdvisor port                  |
| `PROMETHEUS_RETENTION`| 30d                 | How long to keep metrics       |
| `GRAFANA_ADMIN_USER`  | admin               | Grafana admin username         |
| `GRAFANA_ADMIN_PASSWORD`| admin             | Grafana admin password         |
| `SLACK_WEBHOOK_URL`   | —                   | Slack incoming webhook URL     |
| `SLACK_CHANNEL`       | #alerts             | Slack channel for alerts       |
| `DISCORD_WEBHOOK_URL` | —                   | Discord webhook URL            |
| `SMTP_SMARTHOST`      | smtp.gmail.com:587  | SMTP server host:port          |
| `SMTP_FROM`           | alerts@example.com  | Email sender address           |
| `SMTP_AUTH_USERNAME`  | —                   | SMTP username                  |
| `SMTP_AUTH_PASSWORD`  | —                   | SMTP password                  |
| `ALERT_EMAIL_TO`      | you@example.com     | Alert recipient email          |
| `GENERIC_WEBHOOK_URL` | —                   | Generic webhook endpoint       |

### File Structure

```
are-we-up/
├── docker-compose.yml           # Stack orchestration
├── .env.example                 # Environment variable template
├── targets.yml                  # Your monitoring targets
├── agents.json                  # Remote server agents (Node Exporter)
├── prometheus/
│   ├── prometheus.yml           # Prometheus configuration
│   └── alert-rules.yml          # Alerting rules
├── alertmanager/
│   └── alertmanager.yml         # Notification routing
├── blackbox-exporter/
│   └── blackbox.yml             # Probe configurations
├── grafana/
│   ├── provisioning/            # Auto-provisioning configs
│   └── dashboards/              # JSON dashboard definitions
└── remote-agent/
    ├── docker-compose.yml       # Node Exporter for remote servers
    └── setup.sh                 # Automated setup script
```

## Stopping

```bash
docker compose down          # Stop containers (keeps data)
docker compose down -v       # Stop and delete all data
```
