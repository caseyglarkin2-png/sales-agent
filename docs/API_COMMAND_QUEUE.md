# Command Queue API

Live base URL: https://web-production-a6ccf.up.railway.app

Security:
- Admin-only endpoints require `X-Admin-Token: <ADMIN_PASSWORD>` and CSRF header on state-changing methods.
- Obtain a CSRF token from any GET response header `X-CSRF-Token` and include it as `X-CSRF-Token`.

Endpoints

1) List Pending

```bash
curl -s $BASE/api/command-queue/ | jq
```

2) Today’s Moves (ranked by APS)

```bash
curl -s $BASE/api/command-queue/today | jq
```

3) Seed Demo Items (admin + CSRF)

```bash
CSRF=$(curl -s -D - $BASE/health -o /dev/null | awk -F": " '/X-CSRF-Token/ {print $2}' | tr -d '\r\n')
curl -s -X POST $BASE/api/command-queue/seed \
  -H "X-Admin-Token: $ADMIN_PASSWORD" \
  -H "X-CSRF-Token: $CSRF" | jq
```

4) Accept / Dismiss (admin + CSRF)

```bash
CSRF=$(curl -s -D - $BASE/health -o /dev/null | awk -F": " '/X-CSRF-Token/ {print $2}' | tr -d '\r\n')
curl -s -X POST $BASE/api/command-queue/<id>/accept \
  -H "X-Admin-Token: $ADMIN_PASSWORD" -H "X-CSRF-Token: $CSRF" | jq
curl -s -X POST $BASE/api/command-queue/<id>/dismiss \
  -H "X-Admin-Token: $ADMIN_PASSWORD" -H "X-CSRF-Token: $CSRF" | jq
```

UI

- Open Today’s Moves page:
  - $BASE/static/command-queue.html
