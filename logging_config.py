import logging
import sys
import uuid

from flask import Flask, g, has_request_context, request


class RequestFormatter(logging.Formatter):
    def format(self, record):
        if has_request_context():
            record.request_id = getattr(g, "request_id", "no-request")
        else:
            record.request_id = "no-request"
        return super().format(record)


def setup_logging(app: Flask):
    handler = logging.StreamHandler(sys.stdout)
    formatter = RequestFormatter(
        fmt="%(asctime)s [%(levelname)s] request_id=%(request_id)s %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    handler.setFormatter(formatter)
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(app.config.get("LOG_LEVEL", "INFO"))

    @app.before_request
    def assign_request_id():
        g.request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])
        g.request_start = __import__("time").time()

    @app.after_request
    def log_request(response):
        duration_ms = (__import__("time").time() - g.request_start) * 1000
        app.logger.info(
            "%s %s -> %s (%.1fms)",
            request.method,
            request.path,
            response.status_code,
            duration_ms,
        )
        response.headers["X-Request-ID"] = g.request_id
        return response
