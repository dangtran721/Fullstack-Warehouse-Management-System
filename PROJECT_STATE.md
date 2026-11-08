# Warehouse Management System — Project State

## Approved Stack
- Python 3.12
- FastAPI
- PostgreSQL 16
- SQLAlchemy 2.0
- Alembic
- HTML / CSS / Vanilla JavaScript
- Docker Compose
- pytest

## Approved Business Requirements
- Multi-warehouse inventory
- Admin and Staff roles
- Products, categories, units, suppliers, warehouses
- Import, export, transfer, adjustment
- Inventory history and alerts
- JWT access/refresh authentication
- Argon2id password hashing
- Atomic inventory transactions
- Admin may export below zero stock
- Staff may not export beyond available stock
- Completed transactions are immutable

## Execution Policy
- Batch implementation
- Verify each batch before completion
- Preserve approved requirements
- No unapproved scope changes
- No phase transition without verification

## Phase Status
- Phase 0: APPROVED
- Phase 1: APPROVED
- Phase 2: IN PROGRESS
- Phase 3-7: NOT STARTED

## Phase 2
- [x] Python 3.12.9
- [x] pip 24.3.1
- [x] Docker CLI
- [x] Docker Compose
- [x] Docker Engine
- [x] Git
- [x] Workspace selected
- [x] Project structure verified
- [x] Virtual environment verified
- [x] Git ignore verified

## Implementation Batches
1. Environment and workspace — COMPLETED
2. Backend foundation, database and migrations — COMPLETED
3. Authentication, authorization and users — COMPLETED
4. Categories, products and units — COMPLETED
5. Warehouses and suppliers — COMPLETED
6. Inventory, import and export — COMPLETED
7. Transfer, adjustment and alerts — COMPLETED
8. Backend integration tests — PARTIALLY VERIFIED
9. Frontend foundation and authentication — COMPLETED
10. Frontend management screens — COMPLETED
11. End-to-end testing — COMPLETED
12. Deployment preparation and documentation — PARTIALLY VERIFIED

## Current Task
Final handoff is prepared. Browser E2E remains NOT VERIFIED because Playwright is not installed and Work settings disable local browser automation. Docker Compose configuration is valid; image build reached base-image metadata resolution but did not complete in the available environment.

## Batch 8 Verification
- Full regression: 15 tests passed.
- Backend coverage: 94%.
- API integration workflows use isolated SQLite in-memory databases and do not change development data.
- PostgreSQL concurrency: NOT VERIFIED. The psycopg/libpq runtime stalls during PostgreSQL driver startup; no business-logic change was made to work around it.

## Batch 9 Verification
- Frontend authentication client tests: 6 passed (register, login, refresh rotation, logout, current-user request, and validation errors).
- Backend regression plus CORS preflight test: 16 passed, 1 skipped.
- Backend coverage: 94%.
- The frontend is static HTML/CSS/Vanilla JavaScript. It stores the JWT pair in local storage because the approved backend contract returns tokens in JSON rather than secure cookies.

## Batch 10 Status
- Added read-only `GET /api/v1/transfers` with status, warehouse, and offset-pagination filters.
- Added read-only `GET /api/v1/inventory-movements` with warehouse, product, movement-type, and offset-pagination filters. Transfer and adjustment history are available through `movement_type`.
- Management workspace implementation: dashboard, warehouse/product CRUD UI, inventory filters, import/export, transfer, adjustment, and low-stock alert screens.
- The original `.venv` contained macOS cloud-file placeholders (`dataless`) in Pydantic files. It was replaced with an isolated venv using the exact previously installed dependency versions; the original is retained temporarily outside the project at `/private/tmp/wms-venv-cloud-placeholder-backup`.
- Import verification passes for Pydantic 2.14.3, FastAPI 0.162.0, and `app.main`.
- Endpoint tests: 2 passed. Full backend regression: 17 passed, 1 skipped. The existing FastAPI/TestClient deprecation warning remains.

## Batch 11 Verification
- Ran migrations through revision `20261107_0009` on the isolated PostgreSQL database `wms_e2e_batch11`; the database was used only for E2E verification.
- PostgreSQL E2E API test covers registration/login/refresh reuse protection/logout, ADMIN/STAFF authorization, catalog and warehouse access, import/export, transfer, adjustment, alerts, movements, and list filters.
- PostgreSQL row-lock concurrency test passed: concurrent STAFF exports preserve inventory and reject one insufficient export.
- Full backend suite: 19 passed, 1 existing FastAPI/TestClient deprecation warning. Frontend authentication unit tests: 6 passed.
- Browser-driven frontend E2E is not verified: no browser automation runner is configured. Frontend behavior is verified only through unit tests and API-contract coverage.
- Browser smoke follow-up: Google Chrome is installed, but Playwright is unavailable. FastAPI started successfully against isolated `wms_browser_e2e` and `GET /health` returned HTTP 200. Local browser automation is disabled by Work settings, so no browser workflow, console check, or network capture could run. The test database was dropped and temporary servers were stopped; no browser workflow was marked as passed.

## Batch 12 Verification
- Added a minimal API Dockerfile and Docker Compose API service with a healthcheck, environment-based database URL, and no embedded secrets.
- Docker Compose configuration validates. Docker image build began successfully but did not complete after resolving the base image metadata in the available environment.
- README documents Docker/local setup, migrations, static frontend serving, test isolation, account policy, workflows, and verification limits.
- `docs/MANUAL_BROWSER_QA.md` provides the browser smoke checklist required while Work settings block browser automation.

## Final Audit
- DONE: authentication/authorization, catalog and location CRUD, inventory workflows, alerts, PostgreSQL E2E, and PostgreSQL concurrency are backed by the committed test suite.
- PARTIAL: Dockerfile and Compose API service are configured and Compose syntax validates. Docker image build is not verified because both BuildKit context transfer and an `rsync` copy to `/private/tmp` stalled while reading the cloud-managed workspace filesystem.
- NOT VERIFIED: browser UI smoke, console errors, and failed-network capture. Work settings disable local browser automation; use `docs/MANUAL_BROWSER_QA.md` when browser access is available.
- MISSING: no Requirement Specification file exists in the repository, so final requirement traceability relies on approved decisions recorded in this file and the test suite.

## Batch 7 Design Decisions
- Transfers use the same DRAFT/CONFIRMED/CANCELLED workflow and always reject source-stock shortages, including for ADMIN.
- `min_quantity` is nullable per inventory row. Null means no threshold is configured; a row is low stock when its quantity is less than or equal to its configured threshold.
- Adjustments are ADMIN-only, require a reason, are immutable after creation, and cannot make inventory negative.

## Batch 3 Design Decisions
- User identifiers use UUIDs.
- Usernames and emails are normalized to lowercase before persistence.
- Public registration always creates a STAFF account; ADMIN creation is not exposed publicly.
- Passwords require 8–128 characters with at least one letter and one digit, and are hashed with Argon2id.
- Access and refresh JWTs use distinct token types. Refresh tokens are stored only as SHA-256 hashes.
- Refresh token rotation uses a token family. Reuse of a rotated token revokes every still-active token in its family.
- Authentication tests use an isolated in-memory SQLite database and do not change development PostgreSQL data.

## Batch 4 Design Decisions
- Categories and units normalize names by trimming whitespace and storing lowercase values; unit codes and product SKUs are stored uppercase.
- Products use UUID foreign keys to Category and Unit with `RESTRICT` deletion behavior.
- A product may be deleted only while no future business record references it; later inventory migrations must preserve this restriction.
- All catalog lists use offset pagination (`skip`, `limit`); products additionally support search, category, and active-status filters.

## Batch 5 Design Decisions
- Warehouse and supplier codes are normalized to uppercase; names are whitespace-normalized while preserving display capitalization.
- Supplier email is optional and validated but intentionally not unique; supplier code is the business identifier.
- Phone validation accepts a simple international-format representation. Warehouse and supplier deletion is physical only until an inventory transaction references either record; future transaction foreign keys must use `RESTRICT` so referenced records cannot be deleted.
- Warehouse and supplier lists use the existing offset pagination with search and active-status filters.

## Batch 6 Design Decisions
- Inventory quantities use `Numeric(18,3)` and are unique per warehouse/product pair. Quantities may be negative only after an ADMIN confirms an export.
- Import and export orders support multiple products and use `DRAFT → CONFIRMED` or `DRAFT → CANCELLED`. No monetary fields are stored.
- Confirmation locks the order and affected inventory rows in one transaction, records immutable inventory movements, and rejects non-draft confirmation to prevent duplicate updates.
- STAFF may create and confirm inventory documents but cannot confirm an export that exceeds available inventory; ADMIN may do so.
