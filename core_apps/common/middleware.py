from opentelemetry import trace


class TraceIdHeaderMiddleware:
    """Adds ``X-Trace-Id`` to every response so the UI / support can quote it and find the trace in Grafana."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        ctx = trace.get_current_span().get_span_context()
        if ctx and ctx.is_valid:
            response["X-Trace-Id"] = format(ctx.trace_id, "032x")
        return response
