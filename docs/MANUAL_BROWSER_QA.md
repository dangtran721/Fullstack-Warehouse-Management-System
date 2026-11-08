# Manual Browser Smoke Checklist

Use a disposable local PostgreSQL database and start the API on port 8000 plus
the static frontend on port 5500 before testing.

- Register a STAFF user, log in, refresh the page, verify the dashboard loads,
  log out, and confirm `management.html` redirects to login when unauthenticated.
- Sign in as an ADMIN created through an approved local setup. Confirm STAFF can
  read lists but cannot see or execute admin create/edit/delete controls.
- As ADMIN, create/search/edit a warehouse and a product; confirm validation and
  API errors are shown instead of fabricated data.
- Create an import draft and confirm it; check inventory quantity and movement.
  Create and cancel another draft; confirm stock does not change.
- Confirm STAFF export over available stock is rejected; confirm ADMIN can export
  below zero. Create a transfer and verify source/destination quantities.
- Confirm adjustment is ADMIN-only, requires a reason, and rejects a negative
  resulting quantity. Set/unset a warehouse-product threshold and inspect alerts.
- Use browser developer tools to confirm no JavaScript console errors and no
  failed API requests during the above paths. Check loading and empty states.
