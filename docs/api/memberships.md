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
    "role": "operator",
    "organization_id": "<UUID>",
    "user_id": "<UUID>",
    "created_at": "<UTC ISO 8601 timestamp>"
}
```

## Rules

- A membership role is either operator or admin.
- New memberships are assigned operator.

## Duplicate membership

Creating the same User–Organization membership a second time returns 409 Conflict.
Exactly one membership row remains in PostgreSQL.

## Validation

- organization_id path parameter must be a UUID.
- user_id must be a UUID.

## Authorization rules

- The request requires Authorization: Bearer <JWT_bearer_access_token>.
- Only an admin membership in the target organization may create a membership there.
- An operator membership in the target organization returns 403 Forbidden.
- A User without membership in the target organization returns 403 Forbidden.
- A request without a valid access token returns 401 Unauthorized.

## Database shape

organization_memberships model
├── id               UUID primary key
├── role             string, operator or admin, membership role
├── organization_id  required foreign key → organizations.id
├── user_id          required foreign key → users.id
└── created_at       UTC database-generated timestamp

Database constraint: UNIQUE (organization_id, user_id)

## Other

- Unknown organization ID → 403 Forbidden
- Unknown user ID → 404
