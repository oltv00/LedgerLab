# Refresh token API

## POST /auth/refresh

Request

```json
{
    "refresh_token": "<JWT_bearer_refresh_token>"
}
```

Response

200 OK

```json
{
    "access_token": "<JWT_bearer_access_token>",
    "refresh_token": "<JWT_bearer_refresh_token>"
}
```

## POST /auth/logout

Request

```json
{
    "refresh_token": "<JWT_bearer_refresh_token>"
}
```

Response

204 No Content

## Refresh token lifecycle rules

- Refresh tokens are single-use.
- A successful refresh revokes the presented token and returns a replacement refresh token.
- A revoked or already-rotated refresh token returns 401 Unauthorized.
- Logout revokes the submitted active refresh token.
- An access token cannot be used as a refresh token.

## Errors

Status: 401 Unauthorized for missing, malformed, expired, wrong-type, unknown, revoked, or already-rotated refresh tokens.
