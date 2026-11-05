# Package Tracking Project — Development Plan

## 1. Purpose of this document

This file is the project’s development handoff and source of truth.

A new developer or AI agent should read this file before changing the project.

The project is a college containers-course assignment. Its purpose is to
implement a small, functionally correct package-tracking application and later:

1. Build container images.
2. Deploy the application on Red Hat OpenShift.
3. Create CI/CD pipelines.

Prioritize clarity, correctness, and deployment readiness over architectural
complexity.

Do not generate the entire application in one step. Work incrementally,
explain each step, test it, and update the progress section.

---

## 2. Confirmed decisions

The following decisions have been approved by the project owner:

- One modular backend application.
- The TA confirmed that a single backend is allowed.
- Python with FastAPI.
- Synchronous PyMongo.
- Ordinary `def` endpoint handlers for synchronous database operations.
- One React frontend.
- Two GitHub repositories: backend and frontend.
- MongoDB Atlas; the cluster has already been provisioned.
- One application database with multiple collections.
- Database queries initially live inside service modules.
- No separate repository layer.
- No notification service.
- No JWT access/refresh-token system.
- No custom `X-User-ID` interaction.
- Fictional accounts, passwords, addresses, and customer data only.
- Password hashing is intentionally outside the requested classroom scope.
- Backend implementation and API testing precede frontend development.
- The frontend will be developed with AI assistance against the actual API.

Do not introduce microservices, async database access, an ODM, queues,
payments, GPS, or additional services without approval.

This architecture is a modular monolith, not multiple backend microservices.

---

## 3. Pending decisions

The following are proposals, not yet explicitly approved:

1. Use automatic signed cookie sessions for login.
2. Adopt the business rules in section 6.
3. Use soft deletion for admin deletion.
4. Include recipient name and phone in orders.
5. Use the proposed fields, indexes, and endpoint names below.

Resolve these before implementing dependent behavior.

---

## 4. Scope and architecture

### Business context

A business owner creates a delivery order after selling a product.

An administrator assigns a courier.

The courier accepts or declines the assignment and, if accepted, updates
delivery progress.

The business owner can view their orders and delivery status.

### Architecture

React frontend
    |
    | HTTP and JSON
    v
FastAPI backend
    |
    +-- Identity module
    |   +-- Registration
    |   +-- Login/logout
    |   +-- Current account
    |   +-- Courier listing
    |
    +-- Order module
        +-- Create/view/cancel orders
        +-- Assign/reassign couriers
        +-- Accept/decline assignments
        +-- Delivery status updates
        +-- Admin order management
    |
    v
MongoDB Atlas
    |
    +-- PulseShip
        +-- users
        +-- orders

React never connects directly to Atlas.

Identity and Order share the backend process and application database.
Calls between their responsibilities are normal Python/database operations,
not service-to-service HTTP requests.

---

## 5. Simple login proposal

### Recommended mechanism

Use Starlette SessionMiddleware with FastAPI.

Login flow:

1. Client submits email and password.
2. Backend validates credentials.
3. Backend clears any previous session and stores `user_id` in the session.
4. Middleware sets a signed HttpOnly cookie.
5. Later requests send the cookie automatically.
6. Backend resolves the current account from `users`.
7. Backend checks role, order ownership, and assignment.

Do not store passwords or complete user documents in the session.

Do not implement global variables such as `current_user`.
Different browsers and test clients must have independent sessions.

### Endpoints

- POST /api/auth/register
- POST /api/auth/login
- POST /api/auth/logout
- GET /api/auth/me

Registration does not automatically log the account in.

Logout clears the session cookie. This simple signed-cookie design does not
provide server-side revocation of previously copied cookies.

### Session configuration

- Session secret comes from backend configuration.
- Do not hardcode or commit it.
- Keep it stable across restarts and backend replicas.
- Suggested cookie name: PulseShip_session.
- Suggested lifetime: 8 hours.
- HttpOnly enabled.
- SameSite=Lax.
- Secure enabled for HTTPS deployment.
- Secure disabled only for local HTTP development.

Signed session contents are readable, not encrypted.

### Development interaction

Preferred local arrangement:

- Backend: localhost:8000.
- React/Vite: localhost:5173.
- Vite proxies `/api` to the backend.
- React uses relative URLs such as `/api/orders/mine`.

This avoids separate browser-facing API origins.

API documentation served by the backend can be used to log in and then
exercise protected endpoints without manually typing identity headers.

HTTPX/TestClient tests use separate cookie-preserving clients per role.

CLI/API tools must preserve cookies between login and later requests.

### Safety boundary

Plaintext fictional passwords are a deliberate classroom shortcut.
This application is not suitable for real users or production credentials.

- Never reuse real passwords.
- Never return password fields in responses.
- Never log login request bodies.
- Never commit database exports containing passwords.
- Use only fictional recipient data.
- Do not expose it as a public real-user service.

Use JSON request bodies for state-changing operations. Do not use GET for
mutations. Check browser Origin on unsafe requests against the configured
public frontend origin, rejecting mismatches.

SameSite cookies and these restrictions are not a claim of full production
security. Production use would require password hashing, a reviewed
authentication/session design, and comprehensive CSRF protection.

---

## 6. Proposed business rules — confirm before implementation

### Roles

- user: business owner/seller.
- courier: delivery worker.
- admin: manages orders and assignments.

Public registration creates only `user`.

Seed scripts create fictional courier and admin accounts.

No public role selection or role-changing endpoint is required.

### Required order information

- Pickup address.
- Drop-off address.
- Recipient name.
- Recipient phone.
- Package description.
- Requested delivery time.

Optional:

- Package weight.
- Delivery instructions.

No maps, geocoding, tracking coordinates, or payment collection.

Delivery time is a requested time, not an automatically scheduled guarantee.
Use timezone-aware timestamps and store them consistently in UTC.
Reject a requested delivery time in the past at creation.

### Delivery status

PENDING -> PICKED_UP -> IN_TRANSIT -> DELIVERED

PENDING -> CANCELLED

DELIVERED and CANCELLED are terminal.

### Assignment state

UNASSIGNED -> OFFERED -> ACCEPTED

OFFERED -> decline -> UNASSIGNED

Assignment and delivery status are separate fields.

### Creation

A new order has:

- Owner derived from the logged-in account.
- delivery_status = PENDING.
- assignment_state = UNASSIGNED.
- courier_id = null.

The client cannot choose owner, courier, status, or history at creation.

### Business owner permissions

A user can:

- Create orders.
- List their own non-deleted orders.
- Read their own order details.
- Cancel their own PENDING orders.

Cancellation is allowed before pickup, even if a courier has accepted.
Cancellation clears the current assignment and records the change.

### Admin assignment

An admin can assign/reassign only non-deleted PENDING orders.

The selected account must exist, be active, and have role `courier`.

Assignment/reassignment sets:

- courier_id = selected courier.
- assignment_state = OFFERED.

A new courier must accept; acceptance is not inherited from an old assignment.

Reassigning to the same courier is rejected as a no-op.

Do not reassign after pickup in this initial project.

### Courier acceptance/decline

Only the currently offered courier can accept or decline.

Acceptance requires PENDING + OFFERED and sets ACCEPTED.

Decline:

- Records the declined assignment in history.
- Clears courier_id.
- Sets assignment_state to UNASSIGNED.

A declined order does not remain in that courier’s current assigned list.

### Courier status changes

Only the current ACCEPTED courier can update delivery status.

Allowed progression:

- PENDING -> PICKED_UP.
- PICKED_UP -> IN_TRANSIT.
- IN_TRANSIT -> DELIVERED.

No skipping or reversing.

Cancelled/deleted orders cannot progress.

### Admin status changes

Admin may perform the same forward delivery transitions, provided the order
has an accepted courier assignment.

Admin may also cancel a PENDING order.

No arbitrary status strings, backwards transitions, or terminal-state edits.

All admin changes record the acting admin in history.

### Deletion

Proposed behavior: admin soft-deletes orders by setting `deleted_at`.

- Deleted orders disappear from normal lists.
- Normal detail/mutation endpoints return not found for deleted orders.
- Underlying document/history remains.
- No restore screen is required.
- Confirm that this satisfies the TA’s deletion requirement.

---

## 7. Feature coverage

| Feature | Frontend | Backend module |
|---|---|---|
| Registration | Register page | Identity |
| Login | Login page | Identity |
| Create Order page | User form | Order |
| Create Order API | Called by user form | Order |
| My Orders | User order list | Order |
| Order Details/cancel | User details | Order |
| Assigned Orders/accept/decline | Courier dashboard | Order |
| Update delivery status | Courier controls | Order |
| Manage all orders/update/delete | Admin dashboard | Order |
| Assign/reassign courier | Admin controls | Order |

Order details return safe courier information when an assignment exists:
ID, name, and phone. Never return courier password fields.

---

## 8. Repositories and file structure

### Backend repository

package-tracking-backend/
├── plan.md
├── README.md
├── .gitignore
├── .env.example
├── requirements.txt
├── requirements-dev.txt
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── dependencies.py
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── identity.py
│   │   └── orders.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── users.py
│   │   └── orders.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── identity.py
│   │   └── orders.py
│   └── utils/
│       ├── __init__.py
│       └── serialization.py
├── scripts/
│   ├── __init__.py
│   ├── init_db.py
│   └── seed_demo_data.py
├── tests/
│   ├── conftest.py
│   ├── test_identity.py
│   └── test_orders.py
├── docs/
│   └── api-contract.md
├── Dockerfile                  # later
├── deploy/                     # later
└── .github/workflows/          # later

### Responsibilities

- main.py: application creation, middleware, routers, lifecycle, health.
- config.py: validated environment configuration.
- database.py: MongoClient lifecycle and collection access.
- dependencies.py: current account and role checks.
- routers: HTTP inputs, dependencies, responses.
- schemas: Pydantic request/response models.
- services: business rules and PyMongo queries.
- serialization: ObjectId/document-to-response conversion.
- init_db: repeatable collection/index initialization.
- seed_demo_data: repeatable fictional account creation.

Avoid unnecessary classes and abstractions.

### Frontend repository

package-tracking-frontend/
├── README.md
├── .gitignore
├── package.json
├── package-lock.json
├── index.html
├── vite.config.js
├── src/
│   ├── main.jsx
│   ├── App.jsx
│   ├── api/
│   ├── auth/
│   ├── components/
│   ├── pages/
│   │   ├── auth/
│   │   ├── user/
│   │   ├── courier/
│   │   └── admin/
│   └── styles/
├── Dockerfile                  # later
└── .github/workflows/          # later

Use React with JavaScript and Vite unless the team requests otherwise.

---

## 9. Proposed database design

### Database

Application: PulseShip.

An isolated test database is permitted on the same Atlas cluster:
PulseShip_test.

Tests must never clear the application database.

### users collection

- _id: ObjectId.
- name: string.
- email: normalized lowercase string.
- phone: string.
- password: fictional plaintext string, never included in responses.
- role: user | courier | admin.
- active: boolean.
- created_at: UTC datetime.

Normalize email by trimming and lowercasing.
Do not trim or silently modify passwords.

Indexes:

- Unique email.
- Role, if useful for courier listing.

### orders collection

- _id: ObjectId.
- owner_id: ObjectId reference to users.
- recipient:
  - name: string.
  - phone: string.
- pickup:
  - address: string.
- dropoff:
  - address: string.
- package:
  - description: string.
  - weight_kg: optional positive number.
- delivery_instructions: optional string.
- delivery_time: UTC datetime.
- delivery_status: approved enum string.
- courier_id: ObjectId or null.
- assignment_state: approved enum string.
- status_history: array.
- assignment_history: array.
- created_at: UTC datetime.
- updated_at: UTC datetime.
- deleted_at: UTC datetime or null.

History entries include relevant previous/new values, actor ID, and time.

Assignment history additionally identifies the relevant courier and action:
offered, accepted, declined, reassigned, or cleared.

Indexes:

- owner_id + created_at descending.
- courier_id + created_at descending.
- created_at descending for admin listing.

Finalize actual index definitions during database setup.

### Schema strategy

Pydantic validates API requests and defines explicit response models.

MongoDB stores documents; it does not infer a restrictive collection schema
from our Python types.

Start with application validation and indexes.
A MongoDB collection validator is optional and not required initially.

### IDs and dates

- Store references as ObjectId.
- Return IDs as strings.
- Validate incoming IDs before database queries.
- Return malformed IDs as 422, not 500.
- Return dates as ISO 8601 timestamps.
- Never expose raw internal documents indiscriminately.

### Consistency

Keep current status/assignment and histories in the same order document.

For mutations:

1. Check actor permissions.
2. Include expected current state and relevant actor/assignment fields in
   the database update filter.
3. Change current fields and append history in one atomic update.
4. Return 409 if the permitted state changed concurrently.

Avoid a read-check followed by an unconditional update.

---

## 10. Proposed API contract

All business endpoints use the `/api` prefix.

### Identity

| Method | Endpoint | Access |
|---|---|---|
| POST | /api/auth/register | Public; creates user |
| POST | /api/auth/login | Public |
| POST | /api/auth/logout | Clears current session |
| GET | /api/auth/me | Logged in |
| GET | /api/couriers | Admin |

Login accepts JSON email/password and returns safe account information.

### Orders

| Method | Endpoint | Access |
|---|---|---|
| POST | /api/orders | User |
| GET | /api/orders/mine | User |
| GET | /api/orders/assigned | Courier |
| GET | /api/orders | Admin |
| GET | /api/orders/{order_id} | Owner/current courier/admin |
| POST | /api/orders/{order_id}/cancel | Owner or admin; pending |
| PATCH | /api/orders/{order_id}/assignment | Admin |
| POST | /api/orders/{order_id}/accept | Offered courier |
| POST | /api/orders/{order_id}/decline | Offered courier |
| PATCH | /api/orders/{order_id}/status | Accepted courier/admin |
| DELETE | /api/orders/{order_id} | Admin |

Declare fixed paths such as `/mine` and `/assigned` before `/{order_id}`.

Assignment body: courier_id only.
Status body: delivery_status only.

Use strict request schemas to reject unexpected fields.

### List responses

Use pagination:

- page: starts at 1.
- page_size: default 20, maximum 100.
- Sort newest first with a deterministic ID tie-breaker.

Response:

{
  "items": [],
  "total": 0,
  "page": 1,
  "page_size": 20
}

### Status codes

- 201: created.
- 200: successful read/update/login/logout.
- 401: no valid session or invalid login.
- 403: wrong role.
- 404: missing/deleted order or inaccessible order.
- 409: duplicate email, invalid transition, or state conflict.
- 422: invalid request data or malformed ID.
- 503: database unavailable.

Use FastAPI-style `detail` error responses consistently.

### Health

- GET /health/live: process is responding.
- GET /health/ready: database ping succeeds.

Return readiness 503 on database failure.
Do not expose connection strings or internal exception details.

---

## 11. Dependencies and configuration

### Expected runtime dependencies

- fastapi.
- uvicorn.
- pymongo with SRV/DNS support for the Atlas connection.
- pydantic-settings.
- email-validator if using EmailStr.
- itsdangerous for SessionMiddleware.

### Development dependencies

- pytest.
- httpx.

Choose compatible versions during setup and pin tested versions.
Use the same Python version locally and in the backend container.

### Backend environment variables

- MONGODB_URI.
- MONGODB_DATABASE=PulseShip.
- SESSION_SECRET.
- SESSION_HTTPS_ONLY=false locally.
- SESSION_MAX_AGE=28800.
- PUBLIC_ORIGIN=http://localhost:5173.
- Optional TEST_MONGODB_DATABASE=PulseShip_test.

Store local values in ignored `.env`.
Commit `.env.example` with placeholders only.

Do not paste real Atlas credentials into chats, logs, code, or GitHub.

### Connection lifecycle

Use one MongoClient per backend worker process, reused across requests.

Initialize it during application lifecycle and close it on shutdown.
Use bounded database connection timeouts.

Application creation should support test configuration without opening a
production database connection merely because a module was imported.

### Atlas prerequisites

Verify:

- Database user credentials.
- Permissions for the intended application database.
- Development machine network access.
- Atlas connection string.
- OpenShift egress/network access later.

Do not assume that laptop connectivity guarantees OpenShift connectivity.
Do not disable TLS certificate verification.

---

## 12. Development milestones

### Milestone 0 — Confirm pending rules

- Confirm cookie login.
- Confirm section 6 rules.
- Confirm soft deletion and recipient fields.

Output: update this plan with approved decisions.

### Milestone 1 — Bootstrap backend

- Check OS, Python version, editor, and Git status.
- Create backend repository and virtual environment.
- Install dependencies.
- Create minimal working file structure.
- Add configuration.
- Start FastAPI with a liveness endpoint.

Completion: backend starts and interactive docs load.

### Milestone 2 — Connect Atlas and initialize database

- Configure credentials privately.
- Connect with synchronous PyMongo.
- Ping Atlas.
- Implement repeatable init_db script.
- Create collections/indexes.
- Finalize schemas.
- Create idempotent demo-account seed script.

Seed must not delete existing orders or overwrite accounts silently.

Completion: database initialized and fictional accounts available.

### Milestone 3 — Identity APIs

- Registration.
- Login/logout.
- Current account.
- Admin courier listing.
- Session/role dependencies.
- Identity tests.

Completion: independent sessions work and passwords never appear in responses.

### Milestone 4 — User order APIs

- Create.
- My orders.
- Details with safe courier information.
- Cancel.
- Validation and ownership tests.

Completion: user cannot access another owner’s orders.

### Milestone 5 — Admin assignment

- All orders.
- Assign/reassign.
- Courier existence/role validation.
- Assignment history.
- Assignment tests.

Completion: reassigning invalidates the previous courier’s permissions.

### Milestone 6 — Courier workflow

- Assigned order list.
- Accept/decline.
- Forward status transitions.
- State/history tests.

Completion: valid delivery lifecycle works and invalid transitions fail.

### Milestone 7 — Admin management

- Approved status updates.
- Soft deletion.
- Admin tests.

Completion: all listed backend features are implemented.

### Milestone 8 — Backend acceptance

- Run full tests.
- Test the complete scenario manually.
- Document actual request/response examples.
- Verify fresh setup instructions.
- Update docs/api-contract.md.

Do not start frontend generation against an unstable or invented contract.

### Milestone 9 — React frontend

Build incrementally:

1. Login and registration.
2. Session restoration via /api/auth/me.
3. Role-aware navigation and logout.
4. User create/list/detail/cancel pages.
5. Admin list/assign/reassign/update/delete pages.
6. Courier list/accept/decline/status controls.
7. Loading, empty, error, and success states.

Frontend visibility is not backend authorization.

Do not store plaintext passwords in browser storage.
The server session determines identity; frontend account state is display data.

### Milestone 10 — Containers

- One backend image.
- One frontend image.
- Atlas remains external.
- Add local Compose configuration for application containers if useful.
- Backend binds to 0.0.0.0.
- Frontend uses a production static server, not the Vite development server.
- Support non-root/arbitrary-UID deployment.
- Log to stdout/stderr.
- Keep secrets out of images.

Preferred browser architecture:

Browser -> Frontend server
              |
              +-- /api -> Backend
              +-- other paths -> React static files

Configure SPA fallback without hiding API errors.

### Milestone 11 — OpenShift

Proposed resources:

- Backend Deployment and internal Service.
- Frontend Deployment, Service, and HTTPS Route.
- Secrets for Atlas URI and session secret.
- ConfigMaps for non-sensitive configuration.
- Liveness/readiness probes.
- Resource requests/limits.

No MongoDB workload/PVC is needed in OpenShift because Atlas hosts the database.

Enable secure cookies under HTTPS.
Use a stable session secret across backend replicas.
Verify proxy forwarding, public origin, and Atlas egress.

### Milestone 12 — CI/CD

First confirm the course-required pipeline tool.

Expected flow:

Pull request:
- Install dependencies.
- Run tests.
- Build frontend where relevant.

Merge:
- Build affected repository’s image.
- Tag with immutable commit identifier.
- Push to registry.
- Deploy to OpenShift.
- Check rollout.
- Run smoke tests.

CI integration tests need either an isolated database or a separate temporary
MongoDB service. Never run destructive tests against PulseShip.

Keep deployment and database credentials in CI secrets.

---

## 13. Required tests

### Identity/session

- Valid registration.
- Duplicate normalized email.
- Invalid/missing inputs.
- Public registration cannot create admin/courier.
- Correct and incorrect login.
- Current account requires login.
- Logout removes access for that client.
- Independent sessions do not overwrite each other.
- Tampered session cookie is rejected.
- Password omitted from every response.

### Orders

- Valid creation and initial defaults.
- Invalid required fields/delivery time/weight.
- Owner determined by session, not client input.
- My Orders includes only owned orders.
- Cross-owner details/cancel rejected.
- Pending cancellation works.
- Non-pending cancellation fails.
- Admin assignment requires a real active courier.
- Accept/decline requires the offered courier.
- Decline clears assignment and records history.
- Reassignment requires fresh acceptance.
- Old courier cannot update after reassignment.
- Valid delivery progression.
- Skipped/backwards transitions fail.
- Terminal/deleted orders cannot progress.
- Status and history change together.
- Conflicting conditional updates cannot both succeed.
- Admin soft deletion hides orders.
- Pagination behaves correctly.

### Test safety

- Use separate test database configuration.
- Refuse destructive cleanup unless database name is explicitly test-only.
- Tests must not depend on existing demo documents.
- Restore isolated state between tests.

---

## 14. Version control and teamwork

- Keep main runnable.
- Use feature branches.
- Small commits and reviewed pull requests.
- Commit requirements files and frontend package lock.
- Ignore .env, .venv, node_modules, dist, caches, and credentials.
- Document API changes before frontend integration.
- Do not share real credentials through commits or this plan.

Each repository README must include:

- Purpose and architecture.
- Setup and startup.
- Configuration.
- Database initialization/seeding.
- Test commands.
- Demo workflow.
- Known security limitations.
- Container/deployment instructions when implemented.
- Reference to the other repository.

---

## 15. Final acceptance demo

1. Register/login as a business owner.
2. Create an order.
3. Log in as admin and assign a courier.
4. Log in as courier and accept.
5. Mark Picked Up -> In Transit -> Delivered.
6. Business owner sees delivery progress and courier details.

Also demonstrate:

- Pending cancellation.
- Courier decline.
- Admin reassignment.
- Invalid status update rejection.
- Admin deletion.
- Different accounts in separate browser profiles/test clients.
- Successful deployed operation using Atlas.

Definition of done:

- All ten course features work.
- Backend tests pass.
- Fresh setup is documented and reproducible.
- No secrets are committed.
- Frontend handles errors and session expiry.
- Containers run.
- OpenShift deployment works.
- Required CI/CD pipeline works.
- Classroom security shortcuts are documented honestly.

---

## 16. Current progress

### Completed

- [x] Architecture approved: one modular backend.
- [x] FastAPI approved.
- [x] Synchronous PyMongo approved.
- [x] Atlas hosting chosen; cluster reported provisioned.
- [x] Queries inside service modules approved.
- [x] No notifications/JWT/custom identity header.
- [x] Development order agreed.
- [x] Initial plan drafted.

### Not yet completed

- [ ] Cookie login approved.
- [ ] Business rules approved.
- [ ] OS/Python environment confirmed.
- [ ] Repository/files created.
- [ ] Backend starts.
- [ ] Atlas connectivity verified from Python.
- [ ] Collections/indexes initialized.
- [ ] Schemas implemented.
- [ ] Demo accounts seeded.
- [ ] Backend APIs/tests implemented.
- [ ] Frontend implemented.
- [ ] Containerization.
- [ ] OpenShift.
- [ ] CI/CD.

No application files or database changes have been made by the assistant
merely by providing this document.

### Next action

Confirm the pending decisions and development environment.
Then execute Milestone 1 in small steps.

---

## 17. Instructions for a future AI agent

1. Read this plan and inspect existing files before proposing changes.
2. Separate approved decisions from pending proposals.
3. Do not silently add frameworks, services, or security-token systems.
4. Preserve the simple modular backend.
5. Use synchronous PyMongo and def handlers for blocking database operations.
6. Do not replace sessions with X-User-ID, JWTs, or global current-user state.
7. Never request real secrets in chat.
8. Provide small runnable increments with exact filenames and commands.
9. Explain commands for the user’s operating system.
10. Test each milestone before moving on.
11. Do not claim commands/tests/deployments ran unless actually observed.
12. Keep API contracts, README, and this progress section current.
13. Generate frontend code only against implemented backend behavior.
14. Ask before destructive database operations.
15. Keep the project focused on the course’s stated functionality.