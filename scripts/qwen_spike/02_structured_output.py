"""S-02: verify JSON Object mode, schema validation, and repair."""

from typing import Literal

from common import client, print_json, run_case
from pydantic import BaseModel, ConfigDict, Field

MESSAGE = """Hello,
We are evaluating Galician Albariño for specialised wine shops in Germany.
We estimate 600 bottles within 60 days and request a price list and samples.
Best regards, Rhein Selection GmbH
"""


class InquiryAnalysis(BaseModel):
    """Structured commercial inquiry extracted from a message."""

    model_config = ConfigDict(extra="forbid")

    language: str = Field(
        description="ISO 639-1 language code, such as en or es."
    )
    intent: Literal["b2b_purchase_inquiry", "other"]
    market: str | None = Field(
        description="ISO 3166-1 alpha-2 destination country code or null."
    )
    estimated_bottles: int | None = Field(
        ge=1,
        description="Estimated number of bottles or null.",
    )
    channel: str | None = Field(
        description="Commercial sales channel or null."
    )
    target_horizon_days: int | None = Field(
        ge=1,
        description="Target horizon in days or null.",
    )
    samples_requested: bool
    price_list_requested: bool
    missing_fields: list[str] = Field(
        description="Relevant commercial data absent from the message."
    )


def operation() -> tuple[dict[str, object], object]:
    qwen = client()

    return qwen.complete_json(
        [
            {
                "role": "system",
                "content": """
Return only one JSON object.

Use exactly these nine keys and no others:

{
  "language": "ISO 639-1 language code",
  "intent": "b2b_purchase_inquiry or other",
  "market": "ISO 3166-1 alpha-2 code or null",
  "estimated_bottles": "positive integer or null",
  "channel": "commercial channel or null",
  "target_horizon_days": "positive integer or null",
  "samples_requested": "boolean",
  "price_list_requested": "boolean",
  "missing_fields": ["list of absent commercial fields"]
}

All nine keys are mandatory, including nullable fields.
Do not rename, translate, omit, or add keys.
Do not invent absent facts.
""".strip(),
            },
            {
                "role": "user",
                "content": MESSAGE,
            },
        ],
        schema=InquiryAnalysis,
    )


def main() -> None:
    payload, turn = run_case("S-02 structured output", operation)

    print_json(
        {
            "payload": payload,
            "model": turn.model,
            "usage": turn.usage.model_dump(),
        }
    )


if __name__ == "__main__":
    main()
