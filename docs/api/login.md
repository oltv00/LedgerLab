# Login API

POST /auth/login

## Request

```json
{
    "email": "email_value@domain.com",
    "password": "8c647eab31fe"
}
```

## Successful response

200 OK

```json
{
    "access_token": "<JWT_bearer_access_token>",
    "refresh_token": "<JWT_bearer_refresh_token>"
}
```

## Rules

- wrong password -> 401 Unauthorized
- unknown email -> 401 Unauthorized
