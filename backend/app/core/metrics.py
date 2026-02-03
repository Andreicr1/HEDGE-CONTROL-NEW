from prometheus_client import Counter, Histogram


audit_events_total = Counter(
    "audit_events_total",
    "Total audit events recorded",
    ["entity_type", "event_type"],
)

request_latency_seconds = Histogram(
    "request_latency_seconds",
    "Request latency in seconds",
    ["method", "path", "status"],
)