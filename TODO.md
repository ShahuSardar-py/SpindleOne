# Jinja2 TemplateSyntaxError Fix - Cache Clear Plan

## Current Status: [1/5] Create TODO.md ✅

## Steps:

### 1. [✅] Create this TODO.md tracking file
### 2. [ ] Clear Flask instance cache 
### 3. [ ] Clear Python __pycache__
### 4. [ ] Restart Flask server
### 5. [ ] Test /spindlefinance/receivables route

## Commands to run:

```
# Windows CMD (run these in new terminal)
rmdir /s /q instance
for /d /r . %d in (__pycache__) do @if exist "%d" rmdir /s /q "%d"
python run.py
```

## Expected Result:
Visit `http://localhost:5000/spindlefinance/receivables`
Should render without TemplateSyntaxError.

**Findings:** No syntax errors in templates. Error caused by corrupted Flask/Jinja2 cache.

**After server restart:** Mark step 4 ✅ and test route. Reply with result.

