from datetime import datetime
from uuid import uuid4

from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.orm import Session

from app.db.migrations import ensure_entry_claims_number
from app.models import Entry
from app.schemas.entry import EntryCreate, EntryResponse, EntryUpdate


def test_claim_number_survives_create_edit_and_response():
    engine = create_engine("sqlite:///:memory:")
    Entry.__table__.create(engine)
    payload = EntryCreate(claims_number="001-CLAIM", payer_control_num="PAYER-42")
    with Session(engine) as db:
        entry = Entry(
            user_id=uuid4(), user_name="test", worked_date=datetime.now(),
            **payload.model_dump(exclude={"user_name", "worked_date"}),
        )
        db.add(entry)
        db.commit()
        db.expire_all()
        saved = db.scalars(select(Entry)).one()
        response = EntryResponse.model_validate(saved).model_dump()
        assert response["claims_number"] == "001-CLAIM"
        assert response["payer_control_num"] == "PAYER-42"

        update = EntryUpdate(claims_number="002-CLAIM")
        for field, value in update.model_dump(exclude_unset=True).items():
            setattr(saved, field, value)
        db.commit()
        db.expire_all()
        assert EntryResponse.model_validate(saved).claims_number == "002-CLAIM"
        assert saved.payer_control_num == "PAYER-42"
    engine.dispose()


def test_existing_database_migration_preserves_rows_and_is_repeatable():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE entries (id INTEGER PRIMARY KEY, payer_control_num VARCHAR(255))"))
        connection.execute(text("INSERT INTO entries VALUES (1, 'PAYER-42')"))
        ensure_entry_claims_number(connection)
        ensure_entry_claims_number(connection)
        assert "claims_number" in {column["name"] for column in inspect(connection).get_columns("entries")}
        assert connection.execute(text("SELECT payer_control_num, claims_number FROM entries")).one() == ("PAYER-42", None)
    engine.dispose()
