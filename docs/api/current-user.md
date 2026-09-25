# Current User API

GET /auth/me

## Request

```http
Authorization: Bearer <JWT_bearer_access_token>
```

## Successful response

200 OK

```json
{
    "id": "<user_uuid>",
    "name": "user_name_value",
    "email": "email_value@domain.com"
}
```

## Rules

- accept only "access" token, otherwise returns 401 Unauthorized
- missing access token -> 401 Unauthorized
- malformed access token -> 401 Unauthorized
- expired access token -> 401 Unauthorized
- access token with an invalid signature -> 401 Unauthorized
- access token whose `sub` does not identify an existing User -> 401 Unauthorized
- response never exposes `password_hash`
