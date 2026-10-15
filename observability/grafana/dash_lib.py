"""Shared helpers for the dashboard generators (Board = a Grafana dashboard under construction)."""
import json

PROM = {"type": "prometheus", "uid": "prometheus"}
G, O, R = {"color": "green", "value": None}, {"color": "orange", "value": 50}, {"color": "red", "value": 80}
BLUE = [{"color": "blue", "value": None}]


class Board:
    def __init__(self, uid, title, tags, variables):
        self.uid, self.title, self.tags, self.vars = uid, title, tags, variables
        self.panels, self.y, self._id = [], 0, 0

    def _nid(self):
        self._id += 1
        return self._id

    def row(self, title):
        self.panels.append({"id": self._nid(), "type": "row", "title": title, "collapsed": False,
                            "gridPos": {"h": 1, "w": 24, "x": 0, "y": self.y}, "panels": []})
        self.y += 1

    def nxt(self, h):
        self.y += h

    @staticmethod
    def tgt(expr, legend="", ref="A", instant=False):
        t = {"refId": ref, "datasource": PROM, "expr": expr, "legendFormat": legend}
        if instant:
            t.update({"instant": True, "range": False})
        return t

    def stat(self, title, expr, x, w=4, h=4, unit="short", steps=None, desc="", decimals=None):
        fc = {"unit": unit, "thresholds": {"mode": "absolute", "steps": steps or BLUE}, "color": {"mode": "thresholds"}}
        if decimals is not None:
            fc["decimals"] = decimals
        self.panels.append({"id": self._nid(), "type": "stat", "title": title, "description": desc, "datasource": PROM,
            "gridPos": {"h": h, "w": w, "x": x, "y": self.y}, "targets": [self.tgt(expr, instant=True)],
            "fieldConfig": {"defaults": fc, "overrides": []},
            "options": {"reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
                        "colorMode": "background", "graphMode": "none", "textMode": "value", "justifyMode": "center"}})

    def ts(self, title, targets, x, w=12, h=8, unit="short", desc="", stack=False, steps=None, minv=None, maxv=None, bars=False, fill=12):
        custom = {"drawStyle": "bars" if bars else "line", "lineWidth": 2, "fillOpacity": fill, "showPoints": "never",
                  "spanNulls": True, "stacking": {"mode": "normal" if stack else "none", "group": "A"}}
        fc = {"unit": unit, "custom": custom}
        if steps:
            custom["thresholdsStyle"] = {"mode": "line+area"}
            fc["thresholds"] = {"mode": "absolute", "steps": steps}
        if minv is not None: fc["min"] = minv
        if maxv is not None: fc["max"] = maxv
        self.panels.append({"id": self._nid(), "type": "timeseries", "title": title, "description": desc, "datasource": PROM,
            "gridPos": {"h": h, "w": w, "x": x, "y": self.y}, "targets": targets,
            "fieldConfig": {"defaults": fc, "overrides": []},
            "options": {"legend": {"displayMode": "table", "placement": "bottom", "calcs": ["mean", "max", "lastNotNull"]},
                        "tooltip": {"mode": "multi", "sort": "desc"}}})

    def table(self, title, expr, x, w=12, h=8, desc=""):
        self.panels.append({"id": self._nid(), "type": "table", "title": title, "description": desc, "datasource": PROM,
            "gridPos": {"h": h, "w": w, "x": x, "y": self.y},
            "targets": [{**self.tgt(expr, instant=True), "format": "table"}],
            "transformations": [{"id": "organize", "options": {"excludeByName": {"Time": True, "__name__": True, "job": True, "instance": True, "cluster": True}}}],
            "fieldConfig": {"defaults": {}, "overrides": []}, "options": {"showHeader": True, "sortBy": [{"displayName": "Value", "desc": True}]}})

    def gauge(self, title, expr, x, w=4, h=5, unit="percent", steps=None, minv=0, maxv=100, desc=""):
        self.panels.append({"id": self._nid(), "type": "gauge", "title": title, "description": desc, "datasource": PROM,
            "gridPos": {"h": h, "w": w, "x": x, "y": self.y}, "targets": [self.tgt(expr, "{{service}}", instant=True)],
            "fieldConfig": {"defaults": {"unit": unit, "min": minv, "max": maxv, "thresholds": {"mode": "absolute",
                "steps": steps or [{"color": "green", "value": None}, {"color": "orange", "value": 40}, {"color": "red", "value": 80}]}}, "overrides": []},
            "options": {"reduceOptions": {"calcs": ["lastNotNull"]}, "showThresholdMarkers": True}})

    def logs(self, title, expr, x=0, w=24, h=12):
        ds = {"type": "loki", "uid": "loki"}
        self.panels.append({"id": self._nid(), "type": "logs", "title": title, "datasource": ds,
            "gridPos": {"h": h, "w": w, "x": x, "y": self.y},
            "targets": [{"refId": "A", "datasource": ds, "expr": expr, "queryType": "range"}],
            "options": {"showTime": True, "wrapLogMessage": True, "enableLogDetails": True, "sortOrder": "Descending", "dedupStrategy": "none", "prettifyLogMessage": False}})

    def traces(self, title, query, x=0, w=12, h=10):
        ds = {"type": "tempo", "uid": "tempo"}
        self.panels.append({"id": self._nid(), "type": "table", "title": title, "datasource": ds,
            "gridPos": {"h": h, "w": w, "x": x, "y": self.y},
            "targets": [{"refId": "A", "datasource": ds, "queryType": "traceql", "limit": 30, "tableType": "traces", "query": query}],
            "fieldConfig": {"defaults": {}, "overrides": []}, "options": {"showHeader": True}})

    def service_map(self, title="Service map (from traces)", h=10):
        ds = {"type": "tempo", "uid": "tempo"}
        self.panels.append({"id": self._nid(), "type": "nodeGraph", "title": title, "datasource": ds,
            "gridPos": {"h": h, "w": 24, "x": 0, "y": self.y},
            "targets": [{"refId": "A", "datasource": ds, "queryType": "serviceMap"}], "options": {}})

    def save(self, path, refresh="15s", frm="now-1h", extra_links=None):
        dash = {
            "uid": self.uid, "title": self.title, "tags": self.tags, "timezone": "browser", "schemaVersion": 39, "version": 1,
            "editable": True, "graphTooltip": 1, "refresh": refresh, "time": {"from": frm, "to": "now"},
            "links": [{"type": "dashboards", "title": "NextGen Bank dashboards", "tags": ["nextgen"], "asDropdown": True,
                       "includeVars": False, "keepTime": True}] + (extra_links or []),
            "templating": {"list": self.vars},
            "annotations": {"list": [{"name": "Alerts", "type": "dashboard", "datasource": {"type": "grafana", "uid": "-- Grafana --"},
                                      "enable": True, "iconColor": "red", "builtIn": 1}]},
            "panels": self.panels,
        }
        json.dump(dash, open(path, "w"), indent=1)
        print(path, len(self.panels), "panels")


def qvar(name, label, query, multi=True, include_all=True, default_all=True):
    return {"name": name, "label": label, "type": "query", "datasource": PROM, "includeAll": include_all, "multi": multi,
            "allValue": ".+", "refresh": 2, "sort": 1, "query": {"query": query, "refId": f"v-{name}"},
            "current": {"selected": True, "text": "All", "value": "$__all"} if default_all else {}}


# ---- container metrics keyed on the docker compose service (cAdvisor --whitelisted_container_labels)
SVC_LABEL = "container_label_com_docker_compose_service"


def _by_service(expr: str) -> str:
    return f'label_replace({expr}, "service", "$1", "{SVC_LABEL}", "(.+)")'


def cpu_pct(rx=".+"):
    """CPU use as % of the container's CPU limit (`cpus:` in local.yml). Alerts fire above 40 %."""
    usage = _by_service(f'rate(container_cpu_usage_seconds_total{{{SVC_LABEL}=~"{rx}"}}[2m])')
    limit = _by_service(f'container_spec_cpu_quota{{{SVC_LABEL}=~"{rx}"}} / container_spec_cpu_period{{{SVC_LABEL}=~"{rx}"}}')
    return f"100 * sum by (service) ({usage}) / sum by (service) ({limit} > 0)"


def mem_pct(rx=".+"):
    """Working-set memory as % of the container's memory limit (`mem_limit:` in local.yml). Alerts fire above 40 %."""
    usage = _by_service(f'container_memory_working_set_bytes{{{SVC_LABEL}=~"{rx}"}}')
    limit = _by_service(f'container_spec_memory_limit_bytes{{{SVC_LABEL}=~"{rx}"}}')
    return f"100 * sum by (service) ({usage}) / sum by (service) ({limit} > 0)"


def cpu_cores(rx):
    inner = "rate(container_cpu_usage_seconds_total{" + SVC_LABEL + '=~"' + rx + '"}[$__rate_interval])'
    return "sum by (service) (" + _by_service(inner) + ")"


def mem_bytes(rx):
    inner = "container_memory_working_set_bytes{" + SVC_LABEL + '=~"' + rx + '"}'
    return "sum by (service) (" + _by_service(inner) + ")"


G, O, R = {"color": "green", "value": None}, {"color": "orange", "value": 50}, {"color": "red", "value": 80}
BLUE = [{"color": "blue", "value": None}]


class Board:
    def __init__(self, uid, title, tags, variables):
        self.uid, self.title, self.tags, self.vars = uid, title, tags, variables
        self.panels, self.y, self._id = [], 0, 0

    def _nid(self):
        self._id += 1
        return self._id

    def row(self, title):
        self.panels.append({"id": self._nid(), "type": "row", "title": title, "collapsed": False,
                            "gridPos": {"h": 1, "w": 24, "x": 0, "y": self.y}, "panels": []})
        self.y += 1

    def nxt(self, h):
        self.y += h

    @staticmethod
    def tgt(expr, legend="", ref="A", instant=False):
        t = {"refId": ref, "datasource": PROM, "expr": expr, "legendFormat": legend}
        if instant:
            t.update({"instant": True, "range": False})
        return t

    def stat(self, title, expr, x, w=4, h=4, unit="short", steps=None, desc="", decimals=None):
        fc = {"unit": unit, "thresholds": {"mode": "absolute", "steps": steps or BLUE}, "color": {"mode": "thresholds"}}
        if decimals is not None:
            fc["decimals"] = decimals
        self.panels.append({"id": self._nid(), "type": "stat", "title": title, "description": desc, "datasource": PROM,
            "gridPos": {"h": h, "w": w, "x": x, "y": self.y}, "targets": [self.tgt(expr, instant=True)],
            "fieldConfig": {"defaults": fc, "overrides": []},
            "options": {"reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
                        "colorMode": "background", "graphMode": "none", "textMode": "value", "justifyMode": "center"}})

    def ts(self, title, targets, x, w=12, h=8, unit="short", desc="", stack=False, steps=None, minv=None, maxv=None, bars=False, fill=12):
        custom = {"drawStyle": "bars" if bars else "line", "lineWidth": 2, "fillOpacity": fill, "showPoints": "never",
                  "spanNulls": True, "stacking": {"mode": "normal" if stack else "none", "group": "A"}}
        fc = {"unit": unit, "custom": custom}
        if steps:
            custom["thresholdsStyle"] = {"mode": "line+area"}
            fc["thresholds"] = {"mode": "absolute", "steps": steps}
        if minv is not None: fc["min"] = minv
        if maxv is not None: fc["max"] = maxv
        self.panels.append({"id": self._nid(), "type": "timeseries", "title": title, "description": desc, "datasource": PROM,
            "gridPos": {"h": h, "w": w, "x": x, "y": self.y}, "targets": targets,
            "fieldConfig": {"defaults": fc, "overrides": []},
            "options": {"legend": {"displayMode": "table", "placement": "bottom", "calcs": ["mean", "max", "lastNotNull"]},
                        "tooltip": {"mode": "multi", "sort": "desc"}}})

    def table(self, title, expr, x, w=12, h=8, desc=""):
        self.panels.append({"id": self._nid(), "type": "table", "title": title, "description": desc, "datasource": PROM,
            "gridPos": {"h": h, "w": w, "x": x, "y": self.y},
            "targets": [{**self.tgt(expr, instant=True), "format": "table"}],
            "transformations": [{"id": "organize", "options": {"excludeByName": {"Time": True, "__name__": True, "job": True, "instance": True, "cluster": True}}}],
            "fieldConfig": {"defaults": {}, "overrides": []}, "options": {"showHeader": True, "sortBy": [{"displayName": "Value", "desc": True}]}})

    def gauge(self, title, expr, x, w=4, h=5, unit="percent", steps=None, minv=0, maxv=100, desc=""):
        self.panels.append({"id": self._nid(), "type": "gauge", "title": title, "description": desc, "datasource": PROM,
            "gridPos": {"h": h, "w": w, "x": x, "y": self.y}, "targets": [self.tgt(expr, "{{service}}", instant=True)],
            "fieldConfig": {"defaults": {"unit": unit, "min": minv, "max": maxv, "thresholds": {"mode": "absolute",
                "steps": steps or [{"color": "green", "value": None}, {"color": "orange", "value": 40}, {"color": "red", "value": 80}]}}, "overrides": []},
            "options": {"reduceOptions": {"calcs": ["lastNotNull"]}, "showThresholdMarkers": True}})

    def logs(self, title, expr, x=0, w=24, h=12):
        ds = {"type": "loki", "uid": "loki"}
        self.panels.append({"id": self._nid(), "type": "logs", "title": title, "datasource": ds,
            "gridPos": {"h": h, "w": w, "x": x, "y": self.y},
            "targets": [{"refId": "A", "datasource": ds, "expr": expr, "queryType": "range"}],
            "options": {"showTime": True, "wrapLogMessage": True, "enableLogDetails": True, "sortOrder": "Descending", "dedupStrategy": "none", "prettifyLogMessage": False}})

    def traces(self, title, query, x=0, w=12, h=10):
        ds = {"type": "tempo", "uid": "tempo"}
        self.panels.append({"id": self._nid(), "type": "table", "title": title, "datasource": ds,
            "gridPos": {"h": h, "w": w, "x": x, "y": self.y},
            "targets": [{"refId": "A", "datasource": ds, "queryType": "traceql", "limit": 30, "tableType": "traces", "query": query}],
            "fieldConfig": {"defaults": {}, "overrides": []}, "options": {"showHeader": True}})

    def service_map(self, title="Service map (from traces)", h=10):
        ds = {"type": "tempo", "uid": "tempo"}
        self.panels.append({"id": self._nid(), "type": "nodeGraph", "title": title, "datasource": ds,
            "gridPos": {"h": h, "w": 24, "x": 0, "y": self.y},
            "targets": [{"refId": "A", "datasource": ds, "queryType": "serviceMap"}], "options": {}})

    def save(self, path, refresh="15s", frm="now-1h", extra_links=None):
        dash = {
            "uid": self.uid, "title": self.title, "tags": self.tags, "timezone": "browser", "schemaVersion": 39, "version": 1,
            "editable": True, "graphTooltip": 1, "refresh": refresh, "time": {"from": frm, "to": "now"},
            "links": [{"type": "dashboards", "title": "NextGen Bank dashboards", "tags": ["nextgen"], "asDropdown": True,
                       "includeVars": False, "keepTime": True}] + (extra_links or []),
            "templating": {"list": self.vars},
            "annotations": {"list": [{"name": "Alerts", "type": "dashboard", "datasource": {"type": "grafana", "uid": "-- Grafana --"},
                                      "enable": True, "iconColor": "red", "builtIn": 1}]},
            "panels": self.panels,
        }
        json.dump(dash, open(path, "w"), indent=1)
        print(path, len(self.panels), "panels")


def qvar(name, label, query, multi=True, include_all=True, default_all=True):
    return {"name": name, "label": label, "type": "query", "datasource": PROM, "includeAll": include_all, "multi": multi,
            "allValue": ".+", "refresh": 2, "sort": 1, "query": {"query": query, "refId": f"v-{name}"},
            "current": {"selected": True, "text": "All", "value": "$__all"} if default_all else {}}


# ---- container metrics keyed on the docker compose service (cAdvisor --whitelisted_container_labels)
SVC_LABEL = "container_label_com_docker_compose_service"


def _by_service(expr: str) -> str:
    return f'label_replace({expr}, "service", "$1", "{SVC_LABEL}", "(.+)")'


def cpu_pct(rx=".+"):
    """CPU use as % of the container's CPU limit (`cpus:` in local.yml). Alerts fire above 40 %."""
    usage = _by_service(f'rate(container_cpu_usage_seconds_total{{{SVC_LABEL}=~"{rx}"}}[2m])')
    limit = _by_service(f'container_spec_cpu_quota{{{SVC_LABEL}=~"{rx}"}} / container_spec_cpu_period{{{SVC_LABEL}=~"{rx}"}}')
    return f"100 * sum by (service) ({usage}) / sum by (service) ({limit} > 0)"


def mem_pct(rx=".+"):
    """Working-set memory as % of the container's memory limit (`mem_limit:` in local.yml). Alerts fire above 40 %."""
    usage = _by_service(f'container_memory_working_set_bytes{{{SVC_LABEL}=~"{rx}"}}')
    limit = _by_service(f'container_spec_memory_limit_bytes{{{SVC_LABEL}=~"{rx}"}}')
    return f"100 * sum by (service) ({usage}) / sum by (service) ({limit} > 0)"


def cpu_cores(rx):
    return f'sum by (service) ({_by_service(f"rate(container_cpu_usage_seconds_total{{{SVC_LABEL}=~\"{rx}\"}}[$__rate_interval])")})'


def mem_bytes(rx):
    return f'sum by (service) ({_by_service(f"container_memory_working_set_bytes{{{SVC_LABEL}=~\"{rx}\"}}")})'


G, O, R = {"color": "green", "value": None}, {"color": "orange", "value": 40}, {"color": "red", "value": 80}
