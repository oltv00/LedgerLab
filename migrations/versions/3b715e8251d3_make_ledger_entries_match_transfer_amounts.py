"""make ledger entries match transfer amounts

Revision ID: 3b715e8251d3
Revises: 81a3100fabc1
Create Date: 2026-10-01 10:25:17.123291

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3b715e8251d3"
down_revision: str | Sequence[str] | None = "81a3100fabc1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("""
        CREATE FUNCTION validate_ledger_entries_match_transfer_amounts()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        DECLARE
            ledger_pair_is_valid boolean;
        BEGIN
            SELECT
                COUNT(ledger_entry.id) = 2
                AND COUNT(*) FILTER (
                    WHERE ledger_entry.account_id = transfer.source_account_id
                    AND ledger_entry.amount_minor = -transfer.amount_minor
                ) = 1
                AND COUNT(*) FILTER (
                    WHERE ledger_entry.account_id = transfer.destination_account_id
                    AND ledger_entry.amount_minor = transfer.amount_minor
                ) = 1
            INTO ledger_pair_is_valid
            FROM transfers AS transfer
            LEFT JOIN ledger_entries AS ledger_entry
                ON ledger_entry.transfer_id = transfer.id
            WHERE transfer.id = NEW.transfer_id
            GROUP BY
                transfer.id,
                transfer.source_account_id,
                transfer.destination_account_id,
                transfer.amount_minor;

            IF NOT COALESCE(ledger_pair_is_valid, FALSE) THEN
                RAISE EXCEPTION 'Ledger entries must match the transfer accounts and amount'
                    USING ERRCODE = '23514',
                        CONSTRAINT = 'ck_ledger_entries_match_transfer_amounts';
            END IF;

            RETURN NULL;
        END;
        $$;
    """)

    op.execute("""
        CREATE CONSTRAINT TRIGGER ledger_entries_match_transfer_amounts
        AFTER INSERT ON ledger_entries
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW
        EXECUTE FUNCTION validate_ledger_entries_match_transfer_amounts();
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP TRIGGER ledger_entries_match_transfer_amounts ON ledger_entries")
    op.execute("DROP FUNCTION validate_ledger_entries_match_transfer_amounts()")
