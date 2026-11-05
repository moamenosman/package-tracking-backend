# PulseShip API Contract

This document describes the backend implementation currently provided.

Direct local API:
`http://127.0.0.1:8000`

Frontend requests:
Relative `/api/...` URLs through the frontend proxy.

All request/response bodies use JSON where applicable.

## Authentication

POST /api/auth/login sets the HttpOnly session cookie.

Frontend requests use:

```javascript
credentials: "include"
```

Do not supply JWTs, identity headers, or user IDs to authenticate.

GET /api/auth/me restores frontend account state after page refresh.

A 401 from /auth/me means no active login; it is normal on first visit.

## Public account response

```json
{
  "id": "OBJECT_ID_STRING",
  "name": "Demo Seller",
  "email": "seller@example.com",
  "phone": "+15550100001",
  "role": "user",
  "active": true,
  "created_at": "ISO_8601_TIMESTAMP"
}
```

Role values: user, courier, admin.

Passwords never appear in successful account responses.

## Identity endpoints

| Method | Path | Access | Success |
|---|---|---|---|
| POST | /api/auth/register | Public | 201, account |
| POST | /api/auth/login | Public | 200, account |
| POST | /api/auth/logout | Any client | 200, message |
| GET | /api/auth/me | Logged in | 200, account |
| GET | /api/couriers | Admin | 200, paginated accounts |

Registration body:

```json
{
  "name": "Demo Seller",
  "email": "seller@example.com",
  "phone": "+15550100001",
  "password": "fictional-password"
}
```

Role is not accepted. Registration always creates user.
Registration does not automatically log in.

Login body:

```json
{
  "email": "seller@example.com",
  "password": "seller-demo"
}
```

Logout has no request body.

Courier listing returns active courier accounts only.

## Pagination

List endpoints accept:

- page: default 1, minimum 1.
- page_size: default 20, range 1–100.

Response:

```json
{
  "items": [],
  "total": 0,
  "page": 1,
  "page_size": 20
}
```

Orders are sorted newest first with ID as a tie-breaker.
Couriers are sorted by name, then ID.

## Order endpoints

| Method | Path | Access | Success |
|---|---|---|---|
| POST | /api/orders | User | 201, order |
| GET | /api/orders | Admin | 200, paginated orders |
| GET | /api/orders/mine | User | 200, paginated orders |
| GET | /api/orders/assigned | Courier | 200, paginated orders |
| GET | /api/orders/{id} | Owner/current courier/admin | 200, order |
| POST | /api/orders/{id}/cancel | Owner | 200, order |
| PATCH | /api/orders/{id}/assignment | Admin | 200, order |
| POST | /api/orders/{id}/accept | Current courier | 200, order |
| POST | /api/orders/{id}/decline | Current courier | 200, order |
| PATCH | /api/orders/{id}/status | Current courier/admin | 200, order |
| DELETE | /api/orders/{id} | Admin | 200, message |

Cancel, accept, decline, and delete have no request body.

## Create-order body

```json
{
  "recipient": {
    "name": "Demo Recipient",
    "phone": "+15550100010"
  },
  "pickup": {
    "address": "Demo Warehouse"
  },
  "dropoff": {
    "address": "Demo Destination"
  },
  "package": {
    "description": "Two shirts",
    "weight_kg": 1.5
  },
  "delivery_time": "FUTURE_ISO_8601_TIMESTAMP_WITH_TIMEZONE",
  "delivery_instructions": "Call before arrival."
}
```

Required:
- Recipient name and phone.
- Pickup and drop-off address.
- Package description.
- Future timezone-aware delivery_time.

Optional:
- Positive finite weight_kg.
- delivery_instructions.

The timestamp placeholder above is not a valid request value.
Replace it with an actual future timestamp.

Do not submit owner_id, courier_id, status, revision, history, or deleted_at.

## Order response

```json
{
  "id": "ORDER_ID",
  "owner_id": "OWNER_ID",
  "recipient": {
    "name": "Demo Recipient",
    "phone": "+15550100010"
  },
  "pickup": {
    "address": "Demo Warehouse"
  },
  "dropoff": {
    "address": "Demo Destination"
  },
  "package": {
    "description": "Two shirts",
    "weight_kg": 1.5
  },
  "delivery_time": "ISO_8601_TIMESTAMP",
  "delivery_instructions": "Call before arrival.",
  "delivery_status": "PENDING",
  "assignment_state": "UNASSIGNED",
  "courier_id": null,
  "courier": null,
  "status_history": [
    {
      "from_status": null,
      "to_status": "PENDING",
      "actor_id": "OWNER_ID",
      "changed_at": "ISO_8601_TIMESTAMP"
    }
  ],
  "assignment_history": [],
  "created_at": "ISO_8601_TIMESTAMP",
  "updated_at": "ISO_8601_TIMESTAMP"
}
```

Assigned courier information:

```json
{
  "id": "COURIER_ID",
  "name": "Demo Courier",
  "phone": "+15550100002"
}
```

Assignment-history entry:

```json
{
  "action": "offered",
  "previous_courier_id": null,
  "courier_id": "COURIER_ID",
  "actor_id": "ACTOR_ID",
  "changed_at": "ISO_8601_TIMESTAMP"
}
```

Actions:
offered, accepted, declined, reassigned, cleared.

Internal revision and deletion fields are not returned.

## Assignment request

```json
{
  "courier_id": "VALID_COURIER_OBJECT_ID"
}
```

Rules:
- Admin only.
- Order must be PENDING and not deleted.
- Courier must exist, be active, and have courier role.
- Assigning the current courier again returns 409.
- Assignment/reassignment sets OFFERED.
- Previous courier loses access after reassignment.

## Acceptance and decline

- Explicit accept requires PENDING + OFFERED.
- Accept sets ACCEPTED.
- Decline requires PENDING + OFFERED/ACCEPTED.
- Decline clears courier_id and sets UNASSIGNED.
- Pickup may occur directly from OFFERED.
- Direct pickup records automatic acknowledgement.
- Accept/decline after pickup returns 409.

## Delivery-status request

```json
{
  "delivery_status": "PICKED_UP"
}
```

Allowed transitions:

PENDING -> PICKED_UP -> IN_TRANSIT -> DELIVERED

Only the current courier or admin can advance status.
An active courier assignment is required.

No backwards transitions or skipped states.
Do not use this endpoint for cancellation.

## Cancellation

Owner may cancel:
PENDING, PICKED_UP, IN_TRANSIT.

Cancellation:
- Sets CANCELLED.
- Clears current assignment.
- Records history.
- Keeps the order visible in the owner's list.

DELIVERED/CANCELLED cannot be cancelled.

## Soft deletion

Admin DELETE returns:

```json
{
  "message": "Order deleted successfully."
}
```

Deleted documents remain in MongoDB but disappear from normal APIs.

## List behavior

- My Orders: owned, non-deleted orders, including cancelled orders.
- Assigned Orders: current courier's non-deleted orders, including delivered orders.
- All Orders: all non-deleted orders.

## Error responses

Common error:

```json
{
  "detail": "Error message"
}
```

Validation error:

```json
{
  "detail": [
    {
      "loc": ["body", "recipient", "phone"],
      "msg": "Field required",
      "type": "missing"
    }
  ]
}
```

Frontend must handle both string and array detail values.

Status codes:
- 401: login/session required or invalid credentials.
- 403: wrong role or rejected browser Origin.
- 404: missing/deleted/inaccessible order, or invalid courier selection.
- 409: duplicate email, invalid lifecycle action, or concurrent change.
- 422: invalid request data or malformed ID.
- 503: database unavailable.

After 409, refresh the order before offering another action.

## Health

GET /health/live:
200 {"status":"ok"}

GET /health/ready:
200 {"status":"ok","database":"connected"}

Readiness database failure:
503 {"detail":"Database connection unavailable."}

## Source of truth

If this document and the implementation differ:
1. Inspect the actual backend.
2. Inspect /openapi.json.
3. Correct the document or code intentionally.

Do not make the frontend invent unsupported API behavior.