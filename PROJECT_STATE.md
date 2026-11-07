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
4. Categories, products and units
5. Warehouses and suppliers
6. Inventory, import and export
7. Transfer, adjustment and alerts
8. Backend integration tests
9. Frontend foundation and authentication
10. Frontend management screens
11. Frontend integration and fixes
12. End-to-end testing, deployment and documentation

## Current Task
Batch 3 verified. Awaiting approval for categories, products and units.

## Batch 3 Design Decisions
- User identifiers use UUIDs.
- Usernames and emails are normalized to lowercase before persistence.
- Public registration always creates a STAFF account; ADMIN creation is not exposed publicly.
- Passwords require 8–128 characters with at least one letter and one digit, and are hashed with Argon2id.
- Access and refresh JWTs use distinct token types. Refresh tokens are stored only as SHA-256 hashes.
- Refresh token rotation uses a token family. Reuse of a rotated token revokes every still-active token in its family.
- Authentication tests use an isolated in-memory SQLite database and do not change development PostgreSQL data.
