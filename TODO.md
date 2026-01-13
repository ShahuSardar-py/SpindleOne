# TODO: Fix SpindlePeople App Issues

## Phase 1: Core Infrastructure
- [x] 1. Add database config to `app/config.py`
- [x] 2. Initialize SQLAlchemy in `app/extensions.py`
- [x] 3. Register SpindlePeople blueprint in `app/__init__.py`

## Phase 2: Fix SpindlePeople Module
- [x] 4. Fix model typos in `SpindlePeople/models.py` (db.column → db.Column)
- [x] 5. Fix route typo in `SpindlePeople/routes.py` (requet.form → request.form)
- [x] 6. Rename `attendace.html` → `attendance.html`
- [x] 7. Fix field reference in `employees.html` (emp.dept → emp.position)

## Phase 3: Create Missing Templates
- [x] 8. Create `add_employee.html` template
- [x] 9. Create `employee_detail.html` template

## Phase 4: Fix Navigation
- [x] 10. Update `home.html` to navigate to `/hr/attendance`

## Testing
- [ ] Run the app and test navigation to SpindlePeople

