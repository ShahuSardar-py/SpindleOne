import os
import json

LOCK_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'instance', 'lock_state.json')

DEFAULT_STATE = {
    'is_locked': False,
    'lock_reason': 'Access temporarily suspended due to outstanding payment. Please contact system administrator.',
    'passcode': 'zarvec2026'
}

def get_lock_state():
    """Reads the current lock state, creating the file with default values if it doesn't exist."""
    os.makedirs(os.path.dirname(LOCK_FILE), exist_ok=True)
    if not os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE, 'w') as f:
                json.dump(DEFAULT_STATE, f, indent=4)
        except Exception as e:
            print(f"Error creating lock state file: {e}")
        return DEFAULT_STATE.copy()
    
    try:
        with open(LOCK_FILE, 'r') as f:
            state = json.load(f)
            # Ensure all keys are present
            updated = False
            for k, v in DEFAULT_STATE.items():
                if k not in state:
                    state[k] = v
                    updated = True
            if updated:
                with open(LOCK_FILE, 'w') as wf:
                    json.dump(state, wf, indent=4)
            return state
    except Exception as e:
        print(f"Error reading lock state file: {e}")
        return DEFAULT_STATE.copy()

def set_lock_state(is_locked, lock_reason=None, passcode=None):
    """Saves the lock state updates."""
    state = get_lock_state()
    state['is_locked'] = bool(is_locked)
    if lock_reason is not None:
        state['lock_reason'] = str(lock_reason)
    if passcode is not None and passcode.strip():
        state['passcode'] = str(passcode).strip()
    
    os.makedirs(os.path.dirname(LOCK_FILE), exist_ok=True)
    try:
        with open(LOCK_FILE, 'w') as f:
            json.dump(state, f, indent=4)
    except Exception as e:
        print(f"Error saving lock state file: {e}")
    return state
