import os
import sys

# Add root folder to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.zarvec.lock_manager import get_lock_state, set_lock_state

app = create_app()
client = app.test_client()

def test_lockout():
    print("Running Lockout Tests...")
    
    # 1. Reset lock state to unlocked
    set_lock_state(is_locked=False, lock_reason="Access temporarily suspended...", passcode="zarvec2026")
    state = get_lock_state()
    assert state['is_locked'] == False, "Initial lock state should be False"
    print("✓ Initial state verified (Unlocked)")
    
    # 2. Check main page accessibility when unlocked
    res = client.get('/home')
    # Because not logged in, should redirect to /auth/login (302)
    assert res.status_code == 302, f"Expected 302 when unlocked, got {res.status_code}"
    print("✓ Main page accessible (Redirects to login as expected)")
    
    # 3. Check zarvec page accessibility when unlocked
    res = client.get('/zarvec/')
    assert res.status_code == 200, f"Expected 200 for zarvec portal, got {res.status_code}"
    assert b"ZARVEC ACCESS" in res.data or b"Access_Key_Authorization" in res.data, "Should display authentication prompt"
    print("✓ Zarvec panel accessible")
    
    # 4. Turn on lockout
    set_lock_state(is_locked=True, lock_reason="TEST LOCKOUT ACTIVATED")
    state = get_lock_state()
    assert state['is_locked'] == True, "Lock state should be True"
    print("✓ Lockout activated successfully")
    
    # 5. Check main page accessibility when locked
    res = client.get('/home')
    assert res.status_code == 503, f"Expected 503 when locked, got {res.status_code}"
    assert b"ACCESS SUSPENDED" in res.data, "Should display suspension screen"
    assert b"TEST LOCKOUT ACTIVATED" in res.data, "Should display custom suspension message"
    print("✓ Main page blocked with 503 and custom notice message")
    
    # 6. Check zarvec page accessibility when locked
    res = client.get('/zarvec/')
    assert res.status_code == 200, f"Expected 200 for zarvec portal when locked, got {res.status_code}"
    assert b"ZARVEC ACCESS" in res.data or b"Access_Key_Authorization" in res.data, "Should still display authentication prompt even when locked"
    print("✓ Zarvec panel still accessible under lockout")

    # 7. Clean up and unlock
    set_lock_state(is_locked=False)
    print("✓ Cleaned up and unlocked")
    print("ALL TESTS PASSED SUCCESSFULLY!")

if __name__ == '__main__':
    test_lockout()
