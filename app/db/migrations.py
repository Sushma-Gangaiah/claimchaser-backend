from sqlalchemy import inspect, text


def ensure_entry_claims_number(connection):
    """Add the optional claim number to databases created before this field existed."""
    columns = inspect(connection).get_columns("entries")
    if any(column["name"] == "claims_number" for column in columns):
        return
    connection.execute(text("ALTER TABLE entries ADD COLUMN claims_number VARCHAR(255)"))


def ensure_entry_claim_due(connection):
    """Store manually entered amounts; leave historical amounts unknown."""
    columns = inspect(connection).get_columns("entries")
    if not any(column["name"] == "claim_due" for column in columns):
        connection.execute(text("ALTER TABLE entries ADD COLUMN claim_due NUMERIC(15, 2)"))
