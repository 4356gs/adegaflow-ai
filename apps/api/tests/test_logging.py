import json
import logging

from app.core.logging import JsonFormatter


def test_json_formatter_includes_extra_fields() -> None:
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="tool_completed",
        args=(),
        exc_info=None,
    )
    record.correlation_id = "corr-1"

    payload = json.loads(formatter.format(record))

    assert payload["message"] == "tool_completed"
    assert payload["correlation_id"] == "corr-1"
    assert "timestamp" in payload
