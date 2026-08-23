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

## Temporary authorization rule

- This initial bootstrap endpoint is unauthenticated.
- Authentication, organization membership, and administrator authorization will be introduced in the user-and-membership slice.
