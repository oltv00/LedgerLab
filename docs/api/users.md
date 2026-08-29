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

- Email must be syntactically valid after trimming surrounding whitespace.
- LedgerLab does not verify the email domain or mailbox ownership in this slice.

## Temporary authorization rule

- This initial bootstrap endpoint is unauthenticated.
- Authentication, organization membership, and administrator authorization will be introduced in the user-and-membership slice.
