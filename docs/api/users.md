# Users API

POST /users

## Request

```json
{
    "name": "user_name_value",
    "email": "user_email_value"
}
```

## Successful response

```json
{
    "id": "<UUID>",
    "name": "user_name_value",
    "email": "user_email_value",
    "created_at": "<UTC ISO 8601 timestamp>"
}
```

## Initial validation rule

- The user name must be non-empty after trimming surrounding whitespace.
- Email must be syntactically valid after trimming surrounding whitespace.
- LedgerLab does not verify the email domain or mailbox ownership in this slice.

## Duplicate email behavior

- Email must be unique per User.
- The API returns 409 Conflict when POST /users is called with an existing email.

## Temporary authorization rule

- This initial bootstrap endpoint is unauthenticated.
- Authentication, organization membership, and administrator authorization will be introduced in the user-and-membership slice.
