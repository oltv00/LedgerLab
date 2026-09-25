# Ledger

This is not a public endpoint.

## Ledger model

Each ledger entry stores:

- id
- transfer_id
- account_id
- signed amount_minor
- created_at

There is no update or delete operation for ledger entries.
Account balance is the sum of its ledger entry amounts.

## Currency model

- LedgerLab uses one internal sandbox currency.
- All money is integer minor units.
- No float amounts and no currency-conversion scope.

## Rules

- every accepted transfer creates exactly two immutable entries;
- source account entry is `-amount_minor`;
- destination account entry is `+amount_minor`;
- the entries have the same transfer ID;
- their sum is exactly zero;
- if any insert fails, the transfer and both entries do not exist.
