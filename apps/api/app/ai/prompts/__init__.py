"""Versioned prompt resources used by the AdegaFlow AI backend."""

from importlib.resources import files

INQUIRY_ANALYSIS_PROMPT_VERSION = "inquiry_analysis.v1"
PRODUCT_RECOMMENDATION_PROMPT_VERSION = "product_recommendation.v1"


def _load_prompt(version: str) -> str:
    prompt_file = files(__package__).joinpath(f"{version}.md")
    return prompt_file.read_text(encoding="utf-8")


def load_inquiry_analysis_prompt() -> str:
    """Load the packaged prompt used for structured inquiry extraction."""

    return _load_prompt(INQUIRY_ANALYSIS_PROMPT_VERSION)


def load_product_recommendation_prompt() -> str:
    """Load the packaged prompt used for bounded product recommendation."""

    return _load_prompt(PRODUCT_RECOMMENDATION_PROMPT_VERSION)
