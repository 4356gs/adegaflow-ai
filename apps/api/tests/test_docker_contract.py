from pathlib import Path

from app.core.config import Settings


def test_docker_contract_declares_one_worker_healthcheck_volume_and_bounded_queue() -> None:
    root = Path(__file__).resolve().parents[3]
    dockerfile = (root / "apps/api/Dockerfile").read_text(encoding="utf-8")
    compose = (root / "docker-compose.yml").read_text(encoding="utf-8")
    settings = Settings()

    assert '"uvicorn", "app.main:app"' in dockerfile
    assert '"--workers", "1"' in dockerfile
    assert "HEALTHCHECK" in dockerfile
    assert "adegaflow-data:/app/runtime" in compose
    assert 1 <= settings.async_run_queue_capacity <= 100
