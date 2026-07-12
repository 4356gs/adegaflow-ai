from pathlib import Path

from app.db.base import Base
from app.db.models import Customer, CustomerMemory, Inventory, Opportunity, Product
from app.db.seed import load_seed_file, seed_demo_data
from app.db.session import create_database_engine
from sqlalchemy import func, select
from sqlalchemy.orm import Session


def test_demo_seed_is_reproducible(tmp_path: Path) -> None:
    database_path = tmp_path / "seed.db"
    engine = create_database_engine(f"sqlite:///{database_path}")
    Base.metadata.create_all(engine)
    seed_path = Path(__file__).resolve().parents[3] / "data/seeds/demo_seed.json"
    seed = load_seed_file(seed_path)

    with Session(engine) as session:
        first = seed_demo_data(session, seed)
        session.commit()
        second = seed_demo_data(session, seed)
        session.commit()

        assert first == second
        assert second.products == 6
        assert second.inventory == 6
        assert second.customers == 2
        assert second.customer_memories == 4
        assert second.opportunities == 1
        assert session.scalar(select(func.count()).select_from(Product)) == 6
        assert session.scalar(select(func.count()).select_from(Inventory)) == 6
        assert session.scalar(select(func.count()).select_from(Customer)) == 2
        assert session.scalar(select(func.count()).select_from(CustomerMemory)) == 4
        assert session.scalar(select(func.count()).select_from(Opportunity)) == 1

    engine.dispose()


def test_demo_seed_reset_restores_canonical_values(tmp_path: Path) -> None:
    engine = create_database_engine(f"sqlite:///{tmp_path / 'reset.db'}")
    Base.metadata.create_all(engine)
    seed_path = Path(__file__).resolve().parents[3] / "data/seeds/demo_seed.json"
    seed = load_seed_file(seed_path)

    with Session(engine) as session:
        seed_demo_data(session, seed)
        product = session.get(Product, "11111111-1111-4111-8111-111111111111")
        assert product is not None
        product_id = product.id
        product.price_cents = 9999
        session.commit()

        seed_demo_data(session, seed, reset=True)
        session.commit()
        restored = session.get(Product, product_id)
        assert restored is not None
        assert restored.price_cents == 840

    engine.dispose()
