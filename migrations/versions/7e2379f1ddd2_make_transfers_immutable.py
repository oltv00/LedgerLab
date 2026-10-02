"""make transfers immutable

Revision ID: 7e2379f1ddd2
Revises: 3b715e8251d3
Create Date: 2026-10-01 13:02:24.537804

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7e2379f1ddd2"
down_revision: str | Sequence[str] | None = "3b715e8251d3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("""
        CREATE FUNCTION prevent_transfers_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RAISE EXCEPTION 'Transfer entries are immutable'
                USING ERRCODE = '23514',
                    CONSTRAINT = 'ck_transfers_immutable';
        END;
        $$;
    """)

    op.execute("""
        CREATE TRIGGER transfers_prevent_update
        BEFORE UPDATE ON transfers
        FOR EACH ROW
        EXECUTE FUNCTION prevent_transfers_mutation();
    """)

    op.execute("""
        CREATE TRIGGER transfers_prevent_delete
        BEFORE DELETE ON transfers
        FOR EACH ROW
        EXECUTE FUNCTION prevent_transfers_mutation();
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP TRIGGER transfers_prevent_delete ON transfers")
    op.execute("DROP TRIGGER transfers_prevent_update ON transfers")
    op.execute("DROP FUNCTION prevent_transfers_mutation()")
