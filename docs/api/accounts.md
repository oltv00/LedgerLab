# Accounts API

## POST /organizations/{organization_id}/accounts

Header

```
Authorization: Bearer <JWT_bearer_access_token>
```

Access

- `admin` membership role required

Request

```json
{
  "name": "account_name_value"
}
```

Response

201 Created

```json
{
  "id": "<UUID>",
  "name": "account_name_value",
  "organization_id": "<UUID>",
  "created_at": "<UTC ISO 8601 timestamp>"
}
```

Rules

- belongs to exactly one organization;
- has an ID and human-readable name;
- balance is derived from immutable ledger entries, not stored as a mutable account balance.

Errors

- no valid access token → 401
- authenticated caller without target-org membership or required role → 403
- empty/whitespace-only name → 422
