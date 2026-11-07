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
7. Transfer, adjustment and alerts
8. Backend integration tests
9. Frontend foundation and authentication
10. Frontend management screens
11. Frontend integration and fixes
12. End-to-end testing, deployment and documentation

## Current Task
Batch 6 verified. Awaiting approval for transfer, adjustment and alerts.

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
