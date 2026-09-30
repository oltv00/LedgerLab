"""require two ledger entries per transfer

Revision ID: 196dffa4ab3d
Revises: 89ba139ca363
Create Date: 2026-09-30 15:14:16.033440

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "196dffa4ab3d"
down_revision: str | Sequence[str] | None = "89ba139ca363"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("""
        CREATE FUNCTION require_exactly_two_ledger_entries()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        DECLARE
            ledger_entry_count bigint;
        BEGIN
            SELECT COUNT(*)
            INTO ledger_entry_count
            FROM ledger_entries
            WHERE transfer_id = NEW.id;

            IF ledger_entry_count <> 2 THEN
                RAISE EXCEPTION 'A transfer must have exactly two ledger entries'
                    USING ERRCODE = '23514',
                        CONSTRAINT = 'ck_transfers_exactly_two_ledger_entries';
            END IF;

            RETURN NULL;
        END;
        $$;
    """)

    op.execute("""
        CREATE CONSTRAINT TRIGGER transfers_require_exactly_two_ledger_entries
        AFTER INSERT ON transfers
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW
        EXECUTE FUNCTION require_exactly_two_ledger_entries();
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP TRIGGER transfers_require_exactly_two_ledger_entries ON transfers")
    op.execute("DROP FUNCTION require_exactly_two_ledger_entries()")
