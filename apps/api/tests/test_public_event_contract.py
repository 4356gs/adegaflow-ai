import pytest
from app.api.v1.product import _public_event_payload


@pytest.mark.parametrize(
    ("event_type", "payload"),
    [
        ("tool_started", {"tool_name": "search_catalog", "arguments": {"query": "wine"}}),
        ("tool_succeeded", {"tool_name": "check_stock", "result": {"available": 12}}),
        (
            "tool_failed",
            {"tool_name": "get_product_details", "error_code": "TOOL_FAILED", "secret": "x"},
        ),
        (
            "tool_rejected",
            {
                "tool_name": "retrieve_customer_history",
                "reason": "invalid_arguments",
                "customer_email": "buyer@example.test",
            },
        ),
    ],
)
def test_public_tool_events_expose_only_safe_fields(
    event_type: str, payload: dict[str, object]
) -> None:
    public = _public_event_payload(payload)

    assert public["tool_name"] == payload["tool_name"], event_type
    assert set(public) <= {"tool_name", "error_code", "reason"}
    assert "arguments" not in public
    assert "result" not in public
    assert "secret" not in public
    assert "customer_email" not in public


def test_public_non_tool_event_keeps_existing_safe_contract() -> None:
    public = _public_event_payload(
        {"validation_status": "valid", "schema_version": "v1", "raw_payload": {"x": 1}}
    )

    assert public == {"validation_status": "valid", "schema_version": "v1"}
