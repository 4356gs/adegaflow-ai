"""S-03: verify that Qwen requests an allowed local tool."""

from common import client, print_json, run_case

SEARCH_CATALOG_TOOL = {
    "type": "function",
    "function": {
        "name": "search_catalog",
        "description": "Search a fictional winery catalog for products matching buyer needs.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Wine or style to find."},
                "market": {"type": "string", "description": "ISO country code."},
                "limit": {"type": "integer", "minimum": 1, "maximum": 5},
            },
            "required": ["query", "market"],
            "additionalProperties": False,
        },
    },
}


def main() -> None:
    qwen = client()
    turn = run_case(
        "S-03 single tool call",
        lambda: qwen.request_tools(
            [
                {
                    "role": "system",
                    "content": "Use the catalog tool before recommending any product.",
                },
                {
                    "role": "user",
                    "content": "Find Albariño suitable for specialised wine shops in Germany.",
                },
            ],
            tools=[SEARCH_CATALOG_TOOL],
            tool_choice="required",
        ),
    )
    if not turn.tool_calls:
        raise RuntimeError("The model returned no tool call.")
    print_json(turn.model_dump(mode="json"))


if __name__ == "__main__":
    main()
