# Task: Move SpindlePeople templates to module's templates folder

## Goal
Move all spindlepeople templates from `app/templates/spindlepeople/` to `SpindlePeople/templates/spindlepeople/` for clear module differentiation.

## Steps

### 1. Update routes.py
- [ ] Update `render_template` calls to use module templates `spindlepeople/xxx.html`

### 2. Update template files in SpindlePeople/templates/spindlepeople/
- [ ] `add_employee.html` - verify `{% extends "../base.html" %}`
- [ ] `employees.html` - verify `{% extends "../base.html" %}`
- [ ] `attendance.html` - verify `{% extends "../base.html" %}`
- [ ] `employee_detail.html` - verify `{% extends "../base.html" %}`

### 3. Remove old duplicate templates from app/templates/spindlepeople/
- [ ] Delete `app/templates/spindlepeople/add_employee.html`
- [ ] Delete `app/templates/spindlepeople/employees.html`
- [ ] Delete `app/templates/spindlepeople/attendance.html`
- [ ] Delete `app/templates/spindlepeople/employee_detail.html`

### 4. Test
- [ ] Verify app still works correctly

