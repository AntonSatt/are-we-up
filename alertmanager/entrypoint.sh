#!/bin/sh
# Substitute environment variables in the config template using sed
# (envsubst is not available in the alertmanager image)
sed \
  -e "s|\${SLACK_WEBHOOK_URL}|${SLACK_WEBHOOK_URL}|g" \
  -e "s|\${SLACK_CHANNEL}|${SLACK_CHANNEL}|g" \
  -e "s|\${SMTP_SMARTHOST}|${SMTP_SMARTHOST}|g" \
  -e "s|\${SMTP_FROM}|${SMTP_FROM}|g" \
  -e "s|\${SMTP_AUTH_USERNAME}|${SMTP_AUTH_USERNAME}|g" \
  -e "s|\${SMTP_AUTH_PASSWORD}|${SMTP_AUTH_PASSWORD}|g" \
  -e "s|\${ALERT_EMAIL_TO}|${ALERT_EMAIL_TO}|g" \
  -e "s|\${GENERIC_WEBHOOK_URL}|${GENERIC_WEBHOOK_URL}|g" \
  /etc/alertmanager/alertmanager.yml.tmpl > /etc/alertmanager/alertmanager.yml

# Start alertmanager with all passed arguments
exec /bin/alertmanager "$@"
