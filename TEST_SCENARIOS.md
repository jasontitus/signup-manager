# Test Scenarios

This document provides test scenarios to verify the application works correctly.

## Prerequisites

1. Application running: `docker-compose -f docker-compose.yml -f docker-compose.dev.yml up`
2. Frontend: http://localhost:5173
3. Backend: http://localhost:8000
4. Default admin credentials: `admin` / `AdminPassword123!`

---

## Scenario 1: Public Application Submission

**Goal**: Verify anyone can submit an application without authentication.

### Steps:
1. Navigate to http://localhost:5173/apply
2. Fill out the form:
   - First Name: John
   - Last Name: Doe
   - Street Address: 123 Main St, Anytown, CA 12345
   - Phone: 555-0100
   - Email: john.doe@example.com
   - Branch: Army
   - Rank: Sergeant
   - Years of Service: 8
   - Currently Serving: Yes
3. Click "Submit Application"

### Expected Result:
- ✓ Success message displayed
- ✓ Application ID shown
- ✓ Data encrypted in database (check with sqlite3)

### Verification:
```bash
docker-compose exec backend sqlite3 /app/data/members.db
SELECT id, first_name, last_name, _email FROM members;
# _email should be encrypted (not plaintext)
```

---

## Scenario 2: Admin Login and Dashboard

**Goal**: Verify admin can login and access all features.

### Steps:
1. Navigate to http://localhost:5173/login
2. Login with:
   - Username: `admin`
   - Password: `AdminPassword123!`
3. Should redirect to `/admin`

### Expected Result:
- ✓ Successful login
- ✓ Redirected to admin dashboard
- ✓ See 3 tabs: Triage, Database, Staff
- ✓ Can see the pending application from Scenario 1

---

## Scenario 3: Create Vetter User

**Goal**: Create a vetter user for testing isolation.

### Steps:
1. Login as admin (if not already)
2. Go to "Staff" tab
3. Click "Add User"
4. Fill form:
   - Username: `vetter1`
   - Password: `Vetter123!`
   - Full Name: `John Vetter`
   - Role: `Vetter`
5. Click "Create User"

### Expected Result:
- ✓ User created successfully
- ✓ User appears in staff table
- ✓ User is active

### Repeat:
Create a second vetter:
- Username: `vetter2`
- Password: `Vetter456!`
- Full Name: `Jane Vetter`

---

## Scenario 4: Assign Application to Vetter

**Goal**: Verify admin can assign applications to vetters.

### Steps:
1. Login as admin
2. Go to "Triage" tab
3. Find the pending application (John Doe)
4. Click "Assign to Vetter"
5. Select "John Vetter" from dropdown
6. Click "Assign"

### Expected Result:
- ✓ Application status changes to "ASSIGNED"
- ✓ Assignment confirmed
- ✓ Application disappears from Triage tab (no longer pending)

---

## Scenario 5: Vetter Login and View Assigned Member

**Goal**: Verify vetter can only see assigned members.

### Steps:
1. Logout (if logged in as admin)
2. Login with:
   - Username: `vetter1`
   - Password: `Vetter123!`
3. Should redirect to `/vetter`
4. Should see the assigned member (John Doe)

### Expected Result:
- ✓ Vetter dashboard displayed
- ✓ See 1 assigned member
- ✓ Can click on member card

---

## Scenario 6: View Member Details and Decrypt PII

**Goal**: Verify PII decryption and audit logging.

### Steps:
1. Login as `vetter1`
2. Click on assigned member (John Doe)
3. View member details page

### Expected Result:
- ✓ Public info displayed (name, rank, branch)
- ✓ PII section shows decrypted data:
  - Email: john.doe@example.com
  - Phone: 555-0100
  - Address: 123 Main St, Anytown, CA 12345
- ✓ Yellow warning banner about PII being decrypted

### Verification - Check Audit Log:
```bash
docker-compose exec backend sqlite3 /app/data/members.db
SELECT * FROM audit_logs;
# Should see entry with action='VIEWED_PII'
```

---

## Scenario 7: Add Internal Note

**Goal**: Verify vetters can add notes to members.

### Steps:
1. On member detail page (as vetter1)
2. Scroll to "Internal Notes"
3. Type: "Contacted via email, waiting for verification documents"
4. Click "Add Note"

### Expected Result:
- ✓ Note saved
- ✓ Note displayed with timestamp and username
- ✓ Audit log entry created

---

## Scenario 8: Update Member Status

**Goal**: Verify vetters can update member status.

### Steps:
1. On member detail page (as vetter1)
2. Scroll to "Update Status"
3. Click "Mark as Vetted"

### Expected Result:
- ✓ Status changes to "VETTED"
- ✓ Status badge updates to green
- ✓ Audit log entry created

---

## Scenario 9: Vetter Isolation Test (CRITICAL)

**Goal**: Verify vetter A cannot access vetter B's members.

### Setup:
1. Login as admin
2. Submit another application (or use form):
   - Name: Jane Smith
   - Email: jane.smith@example.com
3. Assign this application to `vetter2` (Jane Vetter)
4. Logout

### Test:
1. Login as `vetter1`
2. Note the member ID of Jane Smith's application
3. Try to access directly: http://localhost:5173/members/{jane_id}

### Expected Result:
- ✓ 403 Forbidden error
- ✓ Error message: "You do not have permission to access this member"
- ✓ Vetter1 dashboard should NOT show Jane Smith

### Alternative Test:
1. Login as `vetter1`
2. Open browser dev tools → Network tab
3. Try to access: `http://localhost:8000/api/v1/members/{jane_id}`
4. Should get 403 response

---

## Scenario 10: Admin Can See All Members

**Goal**: Verify admin has full access to all members.

### Steps:
1. Login as admin
2. Go to "Database" tab

### Expected Result:
- ✓ See ALL members (John Doe AND Jane Smith)
- ✓ See member counts by status
- ✓ Can click on any member to view details

---

## Scenario 11: Duplicate Email Prevention

**Goal**: Verify blind index prevents duplicate emails.

### Steps:
1. Navigate to http://localhost:5173/apply
2. Submit application with:
   - Email: john.doe@example.com (same as first application)
   - Other fields: different values

### Expected Result:
- ✓ Error message: "An application with this email address already exists"
- ✓ Application NOT created

---

## Scenario 12: Backend Tests

**Goal**: Run automated tests to verify security.

### Steps:
```bash
cd backend
pip install -r requirements.txt
pytest tests/ -v
```

### Expected Result:
- ✓ test_encryption.py: All pass
- ✓ test_auth.py: All pass
- ✓ test_vetter_isolation.py: All pass (CRITICAL)

---

## Scenario 13: Verify Encryption in Database

**Goal**: Confirm PII is actually encrypted at rest.

### Steps:
```bash
docker-compose exec backend sqlite3 /app/data/members.db
.headers on
SELECT id, first_name, _email, email_blind_index FROM members;
```

### Expected Result:
- ✓ `first_name` is plaintext (e.g., "John")
- ✓ `_email` is encrypted gibberish (e.g., "gAAAAABl...")
- ✓ `email_blind_index` is a SHA256 hash

---

## Scenario 14: Password Change (Admin)

**Goal**: Verify admin can update user passwords.

### Steps:
1. Login as admin
2. Go to "Staff" tab
3. Click on a user (not yourself)
4. Update password
5. Logout and login with new password

### Expected Result:
- ✓ Password updated successfully
- ✓ Can login with new password
- ✓ Cannot login with old password

---

## Scenario 15: Health Check

**Goal**: Verify health endpoint works (for monitoring).

### Steps:
```bash
curl http://localhost:8000/api/v1/health
```

### Expected Result:
```json
{"status":"healthy"}
```

---

## Test Data Summary

After running all scenarios, you should have:

- **2 vetters**: vetter1, vetter2
- **2 members**: John Doe (assigned to vetter1), Jane Smith (assigned to vetter2)
- **Audit logs**: Multiple entries for PII access
- **Verified**: Encryption, RBAC, vetter isolation, duplicate prevention

---

## Cleanup (Start Fresh)

To reset and start over:

```bash
# Stop containers
docker-compose -f docker-compose.yml -f docker-compose.dev.yml down

# Delete database
rm -rf local_data/*

# Restart
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

This will recreate the database and admin user from scratch.

---

## Troubleshooting

### "Cannot connect to backend"
- Check backend is running: `docker-compose ps`
- Check logs: `docker-compose logs backend`

### "Authentication failed"
- Ensure you're using correct credentials
- Check JWT token in browser localStorage

### "Database locked"
- Stop all containers
- Delete `local_data/*.db-wal` and `*.db-shm` files
- Restart

### "Encryption error"
- Verify ENCRYPTION_KEY in .env hasn't changed
- Check backend logs for stack trace
