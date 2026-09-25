# Transfers API

## POST /organizations/{organization_id}/transfers

Header

```
Authorization: Bearer <JWT_bearer_access_token>
```

Access

- `admin` or `operator` membership role

Request

```json
{
  "source_account_id": "<UUID>",
  "destination_account_id": "<UUID>",
  "amount_minor": 1000
}
```

Response

201 Created

```json
{
  "id": "<UUID>",
  "organization_id": "<UUID>",
  "source_account_id": "<UUID>",
  "destination_account_id": "<UUID>",
  "amount_minor": 1000,
  "created_at": "<UTC ISO 8601 timestamp>"
}
```

Rules

- source and destination accounts must belong to the same organization;
- source and destination must differ;
- amount_minor must be an integer greater than zero;
- accepting a transfer posts it immediately—no pending/status lifecycle in this first vertical slice.

Errors

- no valid access token → 401
- authenticated caller without target-org membership or required role → 403
- source/destination account outside target organization → 403
- same source/destination or non-positive amount_minor → 422
