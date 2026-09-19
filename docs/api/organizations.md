# Organizations API

POST /organizations

## Request

```json
{
    "name": "Acme Operations"
}
```

## Successful response

Status: 201 Created

```json
{
    "id": "<UUID>",
    "name": "Acme Operations",
    "created_at": "<UTC ISO 8601 timestamp>"
}
```

## Initial validation rule

- The organization name must be non-empty after trimming surrounding whitespace.

## Authorization and bootstrap rules

- The request requires Authorization: Bearer <JWT_bearer_access_token>.
- An authenticated user can create an organization.
- Creating an organization also creates an organization membership for the authenticated User with role admin.
- The organization and initial admin membership are created in one database transaction.
- A request without a valid access token returns 401 Unauthorized.
