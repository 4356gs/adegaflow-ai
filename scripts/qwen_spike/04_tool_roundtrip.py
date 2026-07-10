"""S-04: execute a local tool and send its result back to Qwen."""

from typing import Any

from common import client, print_json, run_case
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

# Import the tool definition from a file whose name starts with a digit.
_module_path = Path(__file__).with_name("03_single_tool_call.py")
_spec = spec_from_file_location("single_tool_call", _module_path)
assert _spec is not None and _spec.loader is not None
_module = module_from_spec(_spec)
_spec.loader.exec_module(_module)
SEARCH_CATALOG_TOOL = _module.SEARCH_CATALOG_TOOL

CATALOG = [
    {
        "product_id": "demo-1",
        "sku": "ADA-ALB-JOV-2025",
        "name": "Brétema Albariño 2025",
        "price_cents": 840,
        "market_fit": ["DE"],
    },
    {
        "product_id": "demo-2",
        "sku": "ADA-ALB-LIA-2024",
        "name": "Luar sobre Lías 2024",
        "price_cents": 1190,
        "market_fit": ["DE"],
    },
]


def search_catalog(arguments: dict[str, Any]) -> dict[str, Any]:
    query = str(arguments.get("query", "")).lower()
    market = str(arguments.get("market", "")).upper()
    limit = int(arguments.get("limit", 5))
    matches = [
        product
        for product in CATALOG
        if "albariño" in query and market in product["market_fit"]
    ]
    return {"products": matches[:limit], "demo_only": True}


def operation() -> dict[str, Any]:
    qwen = client()
    messages: list[dict[str, Any]] = [
        {
            "role": "system",
            "content": "Use the catalog tool, then summarize the available demo products.",
        },
        {
            "role": "user",
            "content": "Find Albariño for specialised wine shops in Germany.",
        },
    ]

    tool_turn = qwen.request_tools(
        messages,
        tools=[SEARCH_CATALOG_TOOL],
        tool_choice="required",
    )
    if len(tool_turn.tool_calls) != 1:
        raise RuntimeError(f"Expected one tool call, got {len(tool_turn.tool_calls)}.")

    call = tool_turn.tool_calls[0]
    if call.name != "search_catalog":
        raise RuntimeError(f"Unexpected tool: {call.name}")

    result = search_catalog(call.arguments)
    messages.append(tool_turn.as_assistant_message())
    messages.append(
        {
            "role": "tool",
            "tool_call_id": call.id,
            "content": __import__("json").dumps(result),
        }
    )

    final_turn = qwen.request_tools(
        messages,
        tools=[SEARCH_CATALOG_TOOL],
        tool_choice="none",
    )
    return {
        "tool_call": call.model_dump(mode="json"),
        "tool_result": result,
        "final_turn": final_turn.model_dump(mode="json"),
    }


def main() -> None:
    result = run_case("S-04 tool roundtrip", operation)
    print_json(result)


if __name__ == "__main__":
    main()
