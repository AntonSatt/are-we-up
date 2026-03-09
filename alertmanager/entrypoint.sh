#!/bin/sh
# Only substitute specific env vars (not Go template {{.Variables}})
envsubst '${SLACK_WEBHOOK_URL} ${SLACK_CHANNEL} ${SMTP_SMARTHOST} ${SMTP_FROM} ${SMTP_AUTH_USERNAME} ${SMTP_AUTH_PASSWORD} ${ALERT_EMAIL_TO} ${GENERIC_WEBHOOK_URL}' \
  < /etc/alertmanager/alertmanager.yml.tmpl \
  > /etc/alertmanager/alertmanager.yml

# Start alertmanager with all passed arguments
exec /bin/alertmanager "$@"
