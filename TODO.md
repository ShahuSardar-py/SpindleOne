# TODO List: Fix SpindleFinance App Errors

## 1. Fix SpindleFinance/routes.py
- [x] Fix import statement: `from . import spindlefinance` → `from . import bp`
- [x] Fix import statement: `from models import AccountCashFlow` → `from .models import AccountCashFlow`
- [x] Add missing imports: `from flask import request` and `from datetime import datetime`
- [x] Fix typo: `methods='POST'` → `request.method == 'POST'`
- [x] Fix typo: `reuqest.form['description']` → `request.form['description']`
- [x] Define `current_balance` variable before use
- [x] Fix route name: `url_for('spindlefinance.add_cashflow')` → `url_for('spindlefinance.cashflow')`
- [x] Fix template name: `add_cashflow.html` → `addRecord.html`
- [x] Align form fields: `txn_type` should match template's `flow_type`

## 2. Fix SpindleFinance/models.py
- [x] Fix nullable: `nullable='False'` → `nullable=False`
- [x] Fix default: `default=datetime.utcnow().date` → `default=datetime.utcnow().date()`
- [x] Add missing `source` field to match route usage

## 3. Fix SpindleFinance/templates/addRecord.html
- [x] Add missing `current_balance` field
- [x] Rename `flow_type` to `txn_type`
- [x] Rename `category` to `txn_name`

## 4. Test
- [ ] Run the app and verify it works
