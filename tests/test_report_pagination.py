import asyncio
from datetime import date, datetime
from uuid import uuid4
from sqlalchemy import create_engine, UUID
from sqlalchemy.ext.compiler import compiles

@compiles(UUID, "sqlite")
def compile_uuid_for_sqlite(type_, compiler, **kwargs):
    return "CHAR(32)"

from sqlalchemy.orm import Session
from app.models import Entry
from app.routers.admin import get_entries_report

class AsyncAdapter:
    def __init__(self, session):
        self.session = session
    async def execute(self, statement):
        return self.session.execute(statement)

def test_report_pages_filters_and_complete_export():
    engine = create_engine('sqlite:///:memory:')
    Entry.__table__.create(engine)
    with Session(engine) as session:
        timestamp = datetime(2026, 10, 6, 12)
        for i in range(1203):
            session.add(Entry(user_id=uuid4(), user_name='alice' if i < 1101 else 'bob',
                is_draft=False, escalation=i % 2 == 0, submitted_at=timestamp))
        session.add(Entry(user_id=uuid4(), user_name='draft', is_draft=True, submitted_at=timestamp))
        session.commit()
        async def report(skip=0, limit=500, user_name=None, escalation=None, day=date(2026, 10, 6)):
            return await get_entries_report(user_name=user_name, escalation=escalation,
                date_from=day, date_to=day, skip=skip, limit=limit,
                db=AsyncAdapter(session), current_admin=None)
        first = asyncio.run(report())
        second = asyncio.run(report(skip=500))
        last = asyncio.run(report(skip=1000))
        assert first['total'] == second['total'] == last['total'] == 1203
        assert [len(page['items']) for page in (first, second, last)] == [500, 500, 203]
        ids = [entry.id for page in (first, second, last) for entry in page['items']]
        assert len(set(ids)) == 1203  # tied timestamps must not duplicate across pages
        assert first['users'] == ['alice', 'bob']
        filtered = asyncio.run(report(skip=1000, user_name='alice'))
        assert filtered['total'] == 1101 and len(filtered['items']) == 101
        escalated = asyncio.run(report(user_name='alice', escalation=True))
        assert escalated['total'] == 551
        assert all(entry.user_name == 'alice' and entry.escalation for entry in escalated['items'])
        empty = asyncio.run(report(day=date(2026, 10, 7)))
        assert empty == {'items': [], 'total': 0, 'users': []}
        beyond = asyncio.run(report(skip=1500))
        assert beyond['total'] == 1203 and beyond['items'] == []
    engine.dispose()
