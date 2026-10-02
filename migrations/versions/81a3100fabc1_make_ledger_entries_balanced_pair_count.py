"""make ledger entries balanced pair count

Revision ID: 81a3100fabc1
Revises: 196dffa4ab3d
Create Date: 2026-09-30 17:08:13.216891

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "81a3100fabc1"
down_revision: str | Sequence[str] | None = "196dffa4ab3d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("""
        CREATE FUNCTION prevent_to_create_third_ledger_entry_with_equal_transfer_id()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        DECLARE
            ledger_entry_count bigint;
        BEGIN
            SELECT COUNT(*)
            INTO ledger_entry_count
            FROM ledger_entries
            WHERE transfer_id = NEW.transfer_id;

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
        CREATE CONSTRAINT TRIGGER ledger_entries_balanced_pair_count
        AFTER INSERT ON ledger_entries
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW
        EXECUTE FUNCTION prevent_to_create_third_ledger_entry_with_equal_transfer_id();
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP TRIGGER ledger_entries_balanced_pair_count ON ledger_entries")
    op.execute(
        "DROP FUNCTION prevent_to_create_third_ledger_entry_with_equal_transfer_id()"
    )
