"""Generate grafana/dashboards/uptime-overview.json for are-we-up (v2 layout).

The JSON is the provisioned file; this script is its source. Edit here, then:

    python3 grafana/generators/uptime_overview.py grafana/dashboards/uptime-overview.json

Edits made in the Grafana UI are not written back, so port them here too.
"""
import json
import sys

DS = {"type": "prometheus", "uid": "PBFA97CFB590B2093"}
SCOPE = 'job=~"$scope"'
# Display names for legacy label values. The labels themselves stay unchanged:
# renaming them would start new series and reset the SLA history.
LEGACY = {"SHH-Radar": "SSH Radar", "Anton-website": "Portfolio", "Carbonshift": "CarbonShift"}
UP_DOWN = [{
    "type": "value",
    "options": {
        "0": {"text": "DOWN", "color": "red", "index": 1},
        "1": {"text": "UP", "color": "green", "index": 0},
    },
}]


def rename_overrides():
    return [{"matcher": {"id": "byName", "options": old},
             "properties": [{"id": "displayName", "value": new}]} for old, new in LEGACY.items()]


def target(expr, ref="A", legend=None, instant=False, fmt="time_series", interval=None):
    t = {"datasource": DS, "expr": expr, "refId": ref, "instant": instant, "range": not instant,
         "format": fmt}
    if legend:
        t["legendFormat"] = legend
    if interval:
        t["interval"] = interval
    return t


def thresholds(*steps):
    return {"mode": "absolute", "steps": [{"color": c, "value": v} for c, v in steps]}


def stat(pid, title, x, w, expr, unit="none", decimals=None, steps=(("green", None),),
         color_mode="value", description=None):
    defaults = {"unit": unit, "thresholds": thresholds(*steps), "color": {"mode": "thresholds"}}
    if decimals is not None:
        defaults["decimals"] = decimals
    p = {
        "id": pid, "type": "stat", "title": title, "datasource": DS,
        "gridPos": {"x": x, "y": 0, "w": w, "h": 4},
        "targets": [target(expr, instant=True)],
        "fieldConfig": {"defaults": defaults, "overrides": []},
        "options": {"reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
                    "colorMode": color_mode, "graphMode": "none", "textMode": "value",
                    "justifyMode": "center", "orientation": "auto", "wideLayout": True,
                    "showPercentChange": False},
    }
    if description:
        p["description"] = description
    return p


def build():
    panels = []
    # --- Row 1: headline numbers -------------------------------------------
    panels.append(stat(1, "Up", 0, 5, f'sum(probe_success{{{SCOPE}}})', decimals=0,
                       description="Probes succeeding right now."))
    panels.append(stat(2, "Down", 5, 5, f'count(probe_success{{{SCOPE}}} == 0) or vector(0)',
                       decimals=0, steps=(("green", None), ("red", 1)), color_mode="background",
                       description="Probes failing right now."))
    panels.append(stat(3, "Uptime (30d)", 10, 5, f'avg(probe:success_ratio:30d{{{SCOPE}}})',
                       unit="percentunit", decimals=3,
                       steps=(("red", None), ("orange", 0.99), ("green", 0.999)),
                       description="Average of every probe's 30-day success ratio."))
    panels.append(stat(4, "Avg response", 15, 5,
                       f'avg(avg_over_time(probe_duration_seconds{{{SCOPE}}}[$__range]))', unit="s",
                       steps=(("green", None), ("orange", 0.5), ("red", 1)),
                       description="Mean probe duration over the selected time range."))
    panels.append(stat(5, "Next cert expiry", 20, 4,
                       f'min((probe_ssl_earliest_cert_expiry{{{SCOPE}}} - time()) / 86400)',
                       unit="suffix: days", decimals=0,
                       steps=(("red", None), ("orange", 7), ("green", 14)),
                       description="Days until the soonest TLS certificate expires."))

    # --- Row 2: one tile per service ---------------------------------------
    panels.append({
        "id": 6, "type": "stat", "title": "Status", "datasource": DS,
        "gridPos": {"x": 0, "y": 4, "w": 24, "h": 5},
        "targets": [target(f'max by (instance) (probe_success{{{SCOPE}}})', legend="{{instance}}",
                           instant=True)],
        "fieldConfig": {"defaults": {"mappings": UP_DOWN, "color": {"mode": "thresholds"},
                                     "thresholds": thresholds(("red", None), ("green", 1))},
                        "overrides": rename_overrides()},
        "options": {"reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
                    "colorMode": "background", "graphMode": "none", "textMode": "value_and_name",
                    "justifyMode": "center", "orientation": "auto", "wideLayout": True,
                    "showPercentChange": False, "text": {"titleSize": 14, "valueSize": 26}},
    })

    # --- Row 3: availability timeline --------------------------------------
    # min_over_time per step so a short outage inside a step still shows red.
    panels.append({
        "id": 7, "type": "state-timeline", "title": "Availability", "datasource": DS,
        "description": "Green = up, red = down. Each step shows red if any probe in it failed.",
        "gridPos": {"x": 0, "y": 9, "w": 24, "h": 13},
        "targets": [target(f'min by (instance) (min_over_time(probe_success{{{SCOPE}}}[$__interval]))',
                           legend="{{instance}}")],
        "interval": "1m",
        "fieldConfig": {"defaults": {"mappings": UP_DOWN, "color": {"mode": "thresholds"},
                                     "thresholds": thresholds(("red", None), ("green", 1)),
                                     "custom": {"fillOpacity": 85, "lineWidth": 0}},
                        "overrides": rename_overrides()},
        "options": {"mergeValues": True, "showValue": "never", "alignValue": "left",
                    "rowHeight": 0.8, "legend": {"showLegend": False},
                    "tooltip": {"mode": "single", "sort": "none"}},
    })

    # --- Row 4: SLA table --------------------------------------------------
    q = {
        "A": f'max by (instance) (probe:success_ratio:1d{{{SCOPE}}})',
        "B": f'max by (instance) (probe:success_ratio:30d{{{SCOPE}}})',
        "C": f'max by (instance) (probe:success_ratio:365d{{{SCOPE}}})',
        "D": f'max by (instance) (slo:target_ratio{{{SCOPE}}})',
        "E": f'max by (instance) (probe:success_ratio:30d{{{SCOPE}}} >= bool slo:target_ratio{{{SCOPE}}})',
        "F": f'max by (instance) (probe:error_budget_remaining_ratio:30d{{{SCOPE}}})',
        "G": f'max by (instance) (avg_over_time(probe_duration_seconds{{{SCOPE}}}[$__range]))',
        "H": f'max by (instance) ((probe_ssl_earliest_cert_expiry{{{SCOPE}}} - time()) / 86400)',
    }
    names = {"instance": "Service", "Value #B": "30d", "Value #E": "Met (30d)",
             "Value #F": "Budget left (30d)", "Value #D": "SLO", "Value #A": "24h",
             "Value #C": "1 year", "Value #G": "Avg response", "Value #H": "Cert days"}

    def ov(name, *props):
        return {"matcher": {"id": "byName", "options": name},
                "properties": [{"id": k, "value": v} for k, v in props]}

    pct = ("unit", "percentunit")
    table_overrides = [
        ov("Service",
           ("mappings", [{"type": "value", "options": {old: {"text": new, "index": i}
                                                       for i, (old, new) in enumerate(LEGACY.items())}}]),
           ("links", [{"title": "Open site detail",
                       "url": "/d/are-we-up-site-detail?var-target=${__data.fields.Service}&${__url_time_range}"}]),
           ("custom.width", 190)),
        ov("24h", pct, ("decimals", 3)),
        ov("30d", pct, ("decimals", 3)),
        ov("1 year", pct, ("decimals", 3)),
        ov("SLO", pct, ("decimals", 2)),
        ov("Met (30d)",
           ("mappings", [{"type": "value", "options": {"1": {"text": "MET", "color": "green", "index": 0},
                                                       "0": {"text": "MISSED", "color": "red", "index": 1}}}]),
           ("custom.cellOptions", {"type": "color-text"})),
        ov("Budget left (30d)", pct, ("decimals", 0), ("min", 0), ("max", 1),
           ("thresholds", thresholds(("red", None), ("orange", 0.25), ("green", 0.5))),
           ("color", {"mode": "thresholds"}),
           ("custom.cellOptions", {"type": "gauge", "mode": "basic", "valueDisplayMode": "text"})),
        ov("Avg response", ("unit", "s")),
        ov("Cert days", ("decimals", 0),
           ("thresholds", thresholds(("red", None), ("orange", 7), ("green", 14))),
           ("color", {"mode": "thresholds"}),
           ("custom.cellOptions", {"type": "color-text"})),
    ]
    panels.append({
        "id": 8, "type": "table", "title": "SLA", "datasource": DS,
        "description": "Met and budget use the 30-day window; 1 year is shown for context. "
                       "Budget below 0% means the SLO is missed. Click a service for its detail view.",
        "gridPos": {"x": 0, "y": 22, "w": 24, "h": 19},
        "targets": [target(expr, ref=ref, instant=True, fmt="table") for ref, expr in q.items()],
        "transformations": [
            # Join on the service name only: the queries' timestamps can differ by a
            # few ms, which makes "merge" pair rows up wrongly.
            {"id": "filterFieldsByName", "options": {"include": {"pattern": "^(instance|Value #.*)$"}}},
            {"id": "joinByField", "options": {"byField": "instance", "mode": "outer"}},
            {"id": "organize", "options": {
                "excludeByName": {},
                "indexByName": {k: i for i, k in enumerate(names)},
                "renameByName": names}},
            {"id": "sortBy", "options": {"sort": [{"field": "30d", "desc": False}]}},
        ],
        "fieldConfig": {"defaults": {"custom": {"align": "auto", "cellOptions": {"type": "auto"}},
                                     "color": {"mode": "fixed", "fixedColor": "text"}},
                        "overrides": table_overrides},
        "options": {"showHeader": True, "cellHeight": "sm", "footer": {"show": False}},
    })

    # --- Row 5: response times (collapsed) ---------------------------------
    panels.append({
        "id": 9, "type": "row", "title": "Response times", "collapsed": True,
        "gridPos": {"x": 0, "y": 41, "w": 24, "h": 1},
        "panels": [{
            "id": 10, "type": "timeseries", "title": "Response time per service", "datasource": DS,
            "gridPos": {"x": 0, "y": 42, "w": 24, "h": 10},
            "targets": [target(f'max by (instance) (probe_duration_seconds{{{SCOPE}}})',
                               legend="{{instance}}")],
            "fieldConfig": {"defaults": {"unit": "s", "custom": {"lineWidth": 1, "fillOpacity": 0,
                                                                 "showPoints": "never"}},
                            "overrides": rename_overrides()},
            "options": {"legend": {"displayMode": "table", "placement": "right",
                                   "calcs": ["mean", "max"], "showLegend": True},
                        "tooltip": {"mode": "multi", "sort": "desc"}},
        }],
    })

    scope_options = [("All", "blackbox-.*"), ("Public", "blackbox-http"), ("Private", "blackbox-private")]
    return {
        "uid": "are-we-up-overview",
        "title": "Uptime Overview",
        "description": "Status, availability timeline and SLA for every probe.",
        "tags": ["are-we-up", "uptime"],
        "timezone": "browser",
        "editable": True,
        "graphTooltip": 1,
        "refresh": "30s",
        "time": {"from": "now-7d", "to": "now"},
        "schemaVersion": 41,
        "version": 2,
        "links": [{"type": "dashboards", "tags": ["are-we-up"], "asDropdown": True,
                   "title": "Dashboards", "keepTime": True, "includeVars": False}],
        "templating": {"list": [{
            "name": "scope", "label": "Scope", "type": "custom",
            "query": ",".join(f"{t} : {v}" for t, v in scope_options),
            "current": {"text": "All", "value": "blackbox-.*"},
            "options": [{"text": t, "value": v, "selected": t == "All"} for t, v in scope_options],
            "multi": False, "includeAll": False, "hide": 0,
        }]},
        "annotations": {"list": []},
        "panels": panels,
    }


if __name__ == "__main__":
    json.dump(build(), open(sys.argv[1], "w"), indent=2, ensure_ascii=False)
    open(sys.argv[1], "a").write("\n")
