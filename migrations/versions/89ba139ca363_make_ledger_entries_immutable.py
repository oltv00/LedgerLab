"""make ledger_entries immutable

Revision ID: 89ba139ca363
Revises: e4410a782afb
Create Date: 2026-09-30 12:53:38.039675

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "89ba139ca363"
down_revision: str | Sequence[str] | None = "e4410a782afb"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("""
        CREATE FUNCTION prevent_ledger_entry_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RAISE EXCEPTION 'Ledger entries are immutable'
                USING ERRCODE = '23514',
                    CONSTRAINT = 'ck_ledger_entries_immutable';
        END;
        $$;
    """)

    op.execute("""
        CREATE TRIGGER ledger_entries_prevent_update
        BEFORE UPDATE ON ledger_entries
        FOR EACH ROW
        EXECUTE FUNCTION prevent_ledger_entry_mutation();
    """)

    op.execute("""
        CREATE TRIGGER ledger_entries_prevent_delete
        BEFORE DELETE ON ledger_entries
        FOR EACH ROW
        EXECUTE FUNCTION prevent_ledger_entry_mutation();
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP TRIGGER ledger_entries_prevent_delete ON ledger_entries")
    op.execute("DROP TRIGGER ledger_entries_prevent_update ON ledger_entries")
    op.execute("DROP FUNCTION prevent_ledger_entry_mutation()")
