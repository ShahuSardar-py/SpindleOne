import os
from app.extensions import db
from app.auth.models import SystemLock

DEFAULT_STATE = {
    'is_locked': False,
    'lock_reason': 'Access temporarily suspended due to outstanding payment. Please contact system administrator.',
    'passcode': 'zarvec2026'
}

def get_lock_state():
    """Reads the current lock state from the database, creating the record if it doesn't exist."""
    # First, support env var overrides (useful for serverless environments)
    env_locked = os.environ.get("SYSTEM_LOCKED", "").lower() in ("true", "1")
    env_reason = os.environ.get("SYSTEM_LOCK_REASON")
    
    state = DEFAULT_STATE.copy()
    
    try:
        lock = SystemLock.query.first()
        if not lock:
            # Seed the default record
            lock = SystemLock(
                is_locked=DEFAULT_STATE['is_locked'],
                lock_reason=DEFAULT_STATE['lock_reason'],
                passcode=DEFAULT_STATE['passcode']
            )
            db.session.add(lock)
            db.session.commit()
            
        state = {
            'is_locked': lock.is_locked,
            'lock_reason': lock.lock_reason,
            'passcode': lock.passcode
        }
    except Exception as e:
        print(f"Warning: Database lock query failed (reverting to defaults): {e}")
        try:
            db.session.rollback()
        except Exception:
            pass

    if env_locked:
        state['is_locked'] = True
        if env_reason:
            state['lock_reason'] = env_reason
            
    return state

def set_lock_state(is_locked, lock_reason=None, passcode=None):
    """Saves the lock state updates in the database."""
    try:
        lock = SystemLock.query.first()
        if not lock:
            lock = SystemLock(
                is_locked=bool(is_locked),
                lock_reason=str(lock_reason or DEFAULT_STATE['lock_reason']),
                passcode=str(passcode or DEFAULT_STATE['passcode']).strip()
            )
            db.session.add(lock)
        else:
            lock.is_locked = bool(is_locked)
            if lock_reason is not None:
                lock.lock_reason = str(lock_reason)
            if passcode is not None and passcode.strip():
                lock.passcode = str(passcode).strip()
        db.session.commit()
        
        return {
            'is_locked': lock.is_locked,
            'lock_reason': lock.lock_reason,
            'passcode': lock.passcode
        }
    except Exception as e:
        print(f"Error saving lock state to database: {e}")
        try:
            db.session.rollback()
        except Exception:
            pass
        return {
            'is_locked': bool(is_locked),
            'lock_reason': str(lock_reason or DEFAULT_STATE['lock_reason']),
            'passcode': str(passcode or DEFAULT_STATE['passcode']).strip()
        }


