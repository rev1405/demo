# MallHaul - Secure System Development Lifecycle (SSDLC)

Security is a pipeline, not a phase. Every control below maps to code in this
repository so assessors can verify, not just believe.

## Phase 1 - Requirements
- Abuse cases per feature: replayed checkout, cross-mall cart injection,
  illegal state jumps (DELIVERED from PENDING), courier self-assignment.
- Acceptance: every abuse case has a server-side rejection, not a UI guard.

## Phase 2 - Design
- STRIDE threat model per domain:
  - Spoofing        -> signed HMAC session tokens, HttpOnly cookies.
  - Tampering       -> Decimal128 money; state machines (database/enums.py)
                       reject illegal transitions server-side; audit_logs.
  - Repudiation     -> audit_logs on payment, fulfillment, delivery, wallet.
  - Info disclosure -> password_hash stripped at serializer; minimal PII;
                       QR payloads are opaque random codes.
  - DoS             -> rate limiting on auth, checkout, wallet endpoints.
  - Elevation       -> role gates (require_customer / require_ops).
- Data classification: PII / financial / operational. Orders and payments
  retained for audit (no TTL).

## Phase 3 - Implementation
- Passwords: PBKDF2-SHA256, 390k iterations, per-user salt (core/security.py).
- Sessions: HMAC-signed token in HttpOnly + SameSite=Lax cookie (routers/auth.py).
- Validation: Pydantic (app/schemas) at the edge + MongoDB $jsonSchema
  validators (database/validators.py) at rest. Two independent layers.
- Money: Decimal128 everywhere; no floats in storage.
- Concurrency: atomic guarded $inc inventory reservation (checkout_service);
  one-active-cart partial unique index; one-active-vehicle partial index.
- Idempotency: unique partial index on payments.idempotency_key; replayed
  checkout returns the original order.
- Queries: structured filters via the driver only - no string-built queries.

## Phase 4 - Testing (manual test map)
1. Register + login + logout; wrong password rejected generically.
2. Replay POST /api/checkout with the same idempotency_key -> same order.
3. Two concurrent checkouts on the last unit of stock -> exactly one succeeds.
4. POST /api/ops/deliveries/{id}/status DELIVERED while PENDING -> 409.
5. Customer calling /api/ops/* -> 403.
6. 11 rapid logins -> 429.

## Phase 5 - Deployment
- Secrets only via environment variables (.env git-ignored).
- MongoDB Atlas: IP allow-list + least-privilege database user.
- HTTPS at the host; switch session cookie secure=True behind TLS.
- Frontend served same-origin: no CORS surface in production.

## Phase 6 - Monitoring & Response
- audit_logs: every payment, fulfillment, delivery and wallet change.
- Incident runbook: rotate secrets -> rotate token signing key (invalidates
  sessions) -> review audit log -> notify affected users (POPIA-aligned).