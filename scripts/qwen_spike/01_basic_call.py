"""S-01: verify authentication, model availability, and a basic response."""

from common import client, print_json, run_case


def main() -> None:
    qwen = client()
    turn = run_case(
        "S-01 basic call",
        lambda: qwen.complete_text(
            [
                {
                    "role": "user",
                    "content": "Reply with one sentence confirming that the API is available.",
                }
            ]
        ),
    )
    print_json(turn.model_dump(mode="json"))


if __name__ == "__main__":
    main()
