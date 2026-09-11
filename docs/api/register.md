# Register API

POST /auth/register

Request:

```json
{
    "name": "user_name_value",
    "email": "email_value@domain.com",
    "password": "8c647eab31fe"
}
```

## Successful response

201 Created

```json
{
    "id": "<UUID>",
    "name": "user_name_value",
    "email": "user_email_value",
    "created_at": "<UTC ISO 8601 timestamp>"
}
```

## Database rule

- Store password_hash only.
- Never store password plaintext.
- Password must be 12–128 characters.
- Password and password_hash are never returned.
- Existing email → 409 Conflict.
