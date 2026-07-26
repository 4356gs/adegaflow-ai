from __future__ import annotations

import pytest
from app.domain.analysis import InquiryAnalysis
from app.domain.artifacts import EmailDraftNarrative, ProposalNarrative
from app.domain.recommendation import RecommendationDraft
from sqlalchemy.orm import Session

from .fake_qwen import FakeQwenClient


def test_fake_qwen_covers_analysis_tools_recommendation_and_artifacts(
    db_session: Session,
) -> None:
    client = FakeQwenClient(db_session)

    analysis, _ = client.complete_json(
        [{"role": "user", "content": "inquiry"}],
        schema=InquiryAnalysis,
    )
    turns = [
        client.request_tools(
            [{"role": "user", "content": "selection"}],
            tools=[{"type": "function"}],
            model="fake-qwen",
        )
        for _ in range(4)
    ]
    draft, _ = client.complete_json(
        [{"role": "user", "content": "recommend"}],
        schema=RecommendationDraft,
    )
    proposal, _ = client.complete_json(
        [{"role": "user", "content": "proposal"}],
        schema=ProposalNarrative,
    )
    email, _ = client.complete_json(
        [{"role": "user", "content": "email"}],
        schema=EmailDraftNarrative,
    )

    assert analysis["company_name"] == "Rhein Selection GmbH"
    assert [turn.tool_calls[0].name if turn.tool_calls else None for turn in turns] == [
        "search_catalog",
        "get_product_details",
        "check_stock",
        None,
    ]
    assert len(draft["items"]) == 2
    assert proposal["headline"]
    assert email["subject"]
    assert not client.tool_turns
    assert not client.json_payloads


def test_fake_qwen_timeout_is_typed_and_consumed_once(db_session: Session) -> None:
    client = FakeQwenClient(db_session, fail_first_json=True)

    with pytest.raises(Exception) as captured:
        client.complete_json([{"role": "user", "content": "inquiry"}], schema=InquiryAnalysis)

    assert captured.value.info.code == "QWEN_TIMEOUT"  # type: ignore[attr-defined]
    payload, _ = client.complete_json(
        [{"role": "user", "content": "inquiry"}],
        schema=InquiryAnalysis,
    )
    assert payload["market"] == "DE"
