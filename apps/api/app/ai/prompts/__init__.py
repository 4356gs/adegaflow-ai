"""Versioned prompt resources used by the AdegaFlow AI backend."""

from importlib.resources import files

INQUIRY_ANALYSIS_PROMPT_VERSION = "inquiry_analysis.v1"


def load_inquiry_analysis_prompt() -> str:
    """Load the packaged prompt used for structured inquiry extraction."""

    prompt_file = files(__package__).joinpath(f"{INQUIRY_ANALYSIS_PROMPT_VERSION}.md")
    return prompt_file.read_text(encoding="utf-8")
