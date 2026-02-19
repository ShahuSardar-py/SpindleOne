# TODO - SpindleFinance Error Fixes

## Step 1: Fix models.py ✅
- [x] Rename `Client.id` to `Client.client_id`
- [x] Change `Client.contact_info` from Integer to String(255)
- [x] Change `Invoice.created_at` from Date to DateTime
- [x] Fix `Invoice` foreign key reference to use `clients.client_id`

## Step 2: Fix routes.py ✅
- [x] Fix `list_clients` to return correct client_id field
- [x] Fix `list_invoices` to return correct client_id field

## Step 3: Fix frontend templates ✅
- [x] Update receivables.html to use correct API URLs (/finance/invoices, /finance/clients)
- [x] Update addRecord.html to use correct API URLs

## Step 4: Create new migration ✅
- [x] Create alembic migration for field changes (fix_spindlefinance_fields.py)

