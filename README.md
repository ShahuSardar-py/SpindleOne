# SpindleOne

SpindleOne is a modular operational suite for small-to-medium manufacturing factories. It provides essential tools with a focus on simplicity and extensibility.

## Modules

### HR (SpindlePeople)
- Employee management
- Attendance tracking

### Finance (SpindleFinance)
- Cashflow dashboard
- Manual and bulk transaction entry
- Invoice and client management
- Live status updates (OPEN/PAID/OVERDUE)

## Tech Stack
- Backend: Python, Flask, SQLAlchemy
- Frontend: HTML, CSS, Jinja2
- Database: SQLite

## Setup
```
pip install -r requirements.txt
python run.py
```

## Current Issues (SpindleFinance)
1. No installment/partial payment tracking - invoices marked PAID on first full sum, no progress indicators
2. Overdue tags missing on late transactions (only invoice-level)
3. Inflow transactions don't require invoice linking (optional only)
4. No UI for payment progress (e.g., 3/5 installments)

## Milestones
### Short-term (v1.1)
- Add installment support to invoices/transactions
- Enforce invoice linking for inflows
- Per-transaction overdue flags
- Progress bars in invoice views

### Medium-term (v1.2)
- Real-time updates (WebSockets)
- Advanced reporting (PDF/CSV export)
- Role-based access control

### Long-term (v2.0)
- Inventory/Stock module
- Production planning
- Multi-factory support
- PostgreSQL production DB

## Contributing
Fork, branch, PR with clear description.

## License
MIT
