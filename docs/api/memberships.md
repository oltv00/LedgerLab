# Memberships API

POST /organizations/{organization_id}/memberships

## Request

```json
{
    "user_id": "<UUID>"
}
```

## Successful response

201 Created

```json
{
    "id": "<UUID>",
    "organization_id": "<UUID>",
    "user_id": "<UUID>",
    "created_at": "<UTC ISO 8601 timestamp>"
}
```

## Duplicate membership

Creating the same User–Organization membership a second time returns 409 Conflict.
Exactly one membership row remains in PostgreSQL.

## Validation

- organization_id path parameter must be a UUID.
- user_id must be a UUID.

## Temporary authorization rule

- This initial membership-creation endpoint is unauthenticated.
- Membership-management authorization and roles will be added later.

## Database shape

organization_memberships model
├── id               UUID primary key
├── organization_id  required foreign key → organizations.id
├── user_id          required foreign key → users.id
└── created_at       UTC database-generated timestamp

Database constraint: UNIQUE (organization_id, user_id)

## Other

- Unknown organization ID → 404
- Unknown user ID → 404
