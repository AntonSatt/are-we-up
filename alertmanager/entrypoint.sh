#!/bin/sh
cp /etc/alertmanager/alertmanager.yml.tmpl /etc/alertmanager/alertmanager.yml
exec /bin/alertmanager "$@"
