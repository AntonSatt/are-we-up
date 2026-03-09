"""Simple Alertmanager to Discord webhook bridge."""

import json
import os
import sys
import urllib.error
import urllib.request
from http.server import HTTPServer, BaseHTTPRequestHandler

DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK", "")


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length))

        embeds = []
        for alert in body.get("alerts", []):
            status = alert.get("status", "unknown")
            labels = alert.get("labels", {})
            annotations = alert.get("annotations", {})

            if status == "firing":
                color = 0xFF0000  # red
                icon = "\U0001f534"
            else:
                color = 0x00FF00  # green
                icon = "\U0001f7e2"

            severity = labels.get("severity", "unknown").upper()
            name = labels.get("alertname", "Alert")
            instance = labels.get("name", labels.get("instance", "unknown"))

            embeds.append({
                "title": f"{icon} [{severity}] {name}",
                "description": annotations.get("description", annotations.get("summary", "")),
                "color": color,
                "fields": [
                    {"name": "Status", "value": status.upper(), "inline": True},
                    {"name": "Instance", "value": instance, "inline": True},
                ],
            })

        if embeds:
            payload = json.dumps({"embeds": embeds}).encode()
            req = urllib.request.Request(
                DISCORD_WEBHOOK,
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "are-we-up/1.0",
                },
                method="POST",
            )
            try:
                resp = urllib.request.urlopen(req)
                print(f"Discord webhook sent OK: {resp.status}", file=sys.stderr)
            except urllib.error.HTTPError as e:
                body = e.read().decode()
                print(f"Discord webhook error: {e.code} {body}", file=sys.stderr)
            except Exception as e:
                print(f"Discord webhook error: {e}", file=sys.stderr)

        self.send_response(200)
        self.end_headers()

    def log_message(self, fmt, *args):
        print(fmt % args, file=sys.stderr)


if __name__ == "__main__":
    if not DISCORD_WEBHOOK:
        print("WARNING: DISCORD_WEBHOOK not set", file=sys.stderr)
    server = HTTPServer(("0.0.0.0", 9094), Handler)
    print("Discord bridge listening on :9094", file=sys.stderr)
    server.serve_forever()
