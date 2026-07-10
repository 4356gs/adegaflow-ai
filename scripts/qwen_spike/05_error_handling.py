"""S-05/S-06: verify safe configuration and optional authentication errors."""

from app.ai.qwen_client import QwenClient, QwenClientError, QwenNotConfiguredError
from app.core.config import Settings
from common import invalid_credential_test_enabled, print_json


def missing_key_case() -> None:
    qwen = QwenClient(settings=Settings(DASHSCOPE_API_KEY=""))
    try:
        qwen.complete_text([{"role": "user", "content": "hello"}])
    except QwenNotConfiguredError as exc:
        print_json({"case": "missing_key", "result": exc.info.model_dump(mode="json")})
        return
    raise RuntimeError("Missing-key test did not fail as expected.")


def invalid_key_case() -> None:
    if not invalid_credential_test_enabled():
        print_json(
            {
                "case": "invalid_credential",
                "status": "skipped",
                "reason": "Set QWEN_TEST_INVALID_CREDENTIAL=true to make the live request.",
            }
        )
        return

    qwen = QwenClient(settings=Settings(DASHSCOPE_API_KEY="sk-invalid-for-spike"))
    try:
        qwen.complete_text([{"role": "user", "content": "hello"}])
    except QwenClientError as exc:
        print_json(
            {"case": "invalid_credential", "result": exc.info.model_dump(mode="json")}
        )
        return
    raise RuntimeError("Invalid-credential test unexpectedly succeeded.")


def main() -> None:
    missing_key_case()
    invalid_key_case()


if __name__ == "__main__":
    main()
