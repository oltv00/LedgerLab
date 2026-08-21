# LedgerLab

An independently built, multi-tenant payment-operations sandbox API for modeling internal accounts, transfers, immutable ledger entries, and export workflows.

## What the product does

- An administrator creates an organization.
- An operator belongs to one organization.
- The operator creates internal accounts.
- The operator submits a transfer between accounts in that organization.
- LedgerLab records balanced immutable entries.
- Repeating the same transfer request with the same idempotency key does not create another transfer.
- The operator can list only their organization’s transfers.
- The operator requests a CSV export and later checks its status.

## Domain glossary

- Organization — the tenant boundary.
- User — an authenticated person belonging to one organization.
- Role — admin or operator.
- Account — an internal sandbox balance container.
- Transfer — a requested movement between two accounts.
- Ledger entry — an immutable debit or credit record produced by a transfer.
- Idempotency key — a client-generated value that makes a repeated write safe.
- Audit event — an append-only record of a security-relevant action.
- Export job — a background request to produce a CSV.

## Rules

1. A user must not read or mutate another organization’s data.
2. A transfer must create equal-and-opposite ledger effects.
3. A transfer either completes fully or leaves no persisted ledger effect.
4. An accepted idempotency key must never create a second transfer.
5. Ledger entries are never edited or deleted.
6. Monetary values are represented as integer minor units, never floating-point values.
