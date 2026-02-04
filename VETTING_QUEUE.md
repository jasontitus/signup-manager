# Vetting Queue Management

This document explains the automated queue management system for candidate vetting.

## Overview

The Signup Manager includes an automated queue system that ensures candidates are efficiently assigned to vetters and prevents applications from getting stuck if a vetter becomes inactive.

## Key Features

### 1. Auto-Assignment on Login

When a vetter logs in, they are automatically assigned the first pending candidate in the queue.

**How it works:**
- Login endpoint checks if user is a vetter
- Queries for the oldest pending candidate (FIFO)
- Assigns candidate to the vetter
- Sets status to ASSIGNED
- Logs action as AUTO_ASSIGNED

**Code location:** `backend/app/routers/auth.py:96-117`

### 2. Auto-Assignment on Completion

When a vetter completes vetting (marks as VETTED or REJECTED), they are automatically assigned the next pending candidate.

**How it works:**
- Status update endpoint checks if new status is VETTED or REJECTED
- Checks if current user is a vetter
- Automatically assigns next pending candidate
- Logs action as AUTO_ASSIGNED

**Code location:** `backend/app/routers/members.py:136-139`

### 3. Manual Next Candidate Request

Vetters can manually request their next assignment using the "Get Next Candidate" button.

**Endpoint:** `POST /api/v1/members/next-candidate`

**Permissions:** Vetter role only

**How it works:**
- Vetter clicks "Get Next Candidate" button
- System assigns next pending candidate
- UI refreshes to show new assignment
- Shows message if no pending candidates available

**Code location:**
- Backend: `backend/app/routers/members.py:198-213`
- Frontend: `frontend/src/pages/VetterDashboard.jsx`

### 4. Stale Assignment Reclamation

Candidates assigned for more than 7 days are automatically returned to the pending queue.

**Threshold:** 7 days (configurable via `STALE_ASSIGNMENT_DAYS` constant)

**Automatic triggers:**
- When any vetter logs in
- When any vetter requests next candidate
- Before auto-assigning any new candidate

**Manual trigger:**
- Admins can click "Reclaim Stale Assignments" in Database tab
- Endpoint: `POST /api/v1/members/reclaim-stale`

**How it works:**
1. Query for members with status=ASSIGNED and updated_at older than 7 days
2. Reset status to PENDING
3. Clear assigned_vetter_id
4. Log each reclamation with action ASSIGNMENT_RECLAIMED
5. Return count of reclaimed assignments

**Code location:** `backend/app/routers/auth.py:18-51`

## Assignment Algorithm

### Priority Order (FIFO)

Candidates are assigned in First-In-First-Out order based on their `created_at` timestamp.

```sql
SELECT * FROM members
WHERE status = 'PENDING'
ORDER BY created_at ASC
LIMIT 1
```

This ensures:
- Oldest applications are processed first
- Fair distribution of workload
- No candidates are accidentally skipped

### Status Flow

```
PUBLIC APPLICATION
    ↓
PENDING (in queue)
    ↓
AUTO-ASSIGNED → ASSIGNED (to vetter)
    ↓
    ├─→ VETTED (approved)
    ├─→ REJECTED (denied)
    └─→ PENDING (if stale, after 7 days)
```

## Audit Trail

All assignment actions are logged in the `audit_logs` table:

### Action Types

| Action | Description | Triggered By |
|--------|-------------|--------------|
| `AUTO_ASSIGNED` | Candidate automatically assigned to vetter | Login, completion, manual request |
| `ASSIGNMENT_RECLAIMED` | Stale assignment returned to queue | Automatic (7 days) or manual admin action |
| `STALE_CHECK` | Stale assignments checked and reclaimed | Before auto-assignment |
| `MANUAL_STALE_RECLAIM` | Admin manually triggered stale reclamation | Admin clicking button |
| `ASSIGNED` | Admin manually assigned candidate to vetter | Admin manual assignment |

### Viewing Audit Logs

```sql
-- View all assignment actions
SELECT * FROM audit_logs
WHERE action IN ('AUTO_ASSIGNED', 'ASSIGNMENT_RECLAIMED', 'STALE_CHECK', 'ASSIGNED')
ORDER BY timestamp DESC;

-- View stale reclamations
SELECT * FROM audit_logs
WHERE action = 'ASSIGNMENT_RECLAIMED'
ORDER BY timestamp DESC;

-- View auto-assignments for specific vetter
SELECT * FROM audit_logs
WHERE action = 'AUTO_ASSIGNED' AND user_id = 2
ORDER BY timestamp DESC;
```

## Configuration

### Stale Assignment Threshold

Default: 7 days

To change, edit `STALE_ASSIGNMENT_DAYS` in `backend/app/routers/auth.py:15`

```python
# Stale assignment threshold (7 days)
STALE_ASSIGNMENT_DAYS = 7
```

**Important:** Changing this value affects when assignments are automatically reclaimed. Consider the following:
- Lower values (e.g., 3 days): More aggressive reclamation, useful if vetters should work quickly
- Higher values (e.g., 14 days): More lenient, useful if vetting requires extensive research

## User Experience

### For Vetters

**Login Flow:**
1. Enter credentials and click "Login"
2. Redirected to dashboard
3. See newly assigned candidate in "Assigned to Me" section
4. Click on candidate to start vetting

**Completion Flow:**
1. Review candidate details
2. Click "Mark as Vetted" or "Reject"
3. Automatically redirected back to dashboard
4. See next assigned candidate ready to review

**Manual Request:**
1. Click "Get Next Candidate" button
2. See success message if candidate available
3. New candidate appears in list
4. See "No pending candidates" message if queue is empty

### For Admins

**Manual Assignment (Optional):**
- Go to Triage tab
- Click "Assign to Vetter" on any pending candidate
- Select specific vetter from dropdown
- Candidate immediately assigned

**Stale Reclamation:**
- Go to Database tab
- Click "Reclaim Stale Assignments"
- See message showing how many assignments were reclaimed
- Reclaimed candidates return to pending queue

**Monitoring:**
- Database tab shows counts: Pending, Assigned, Vetted
- Check audit logs to see assignment history
- Identify inactive vetters by checking stale reclamations

## API Reference

### POST /api/v1/members/next-candidate

Get next pending candidate (auto-assigns to current vetter).

**Authentication:** Required (Vetter role)

**Request:** Empty body

**Response:**
```json
{
  "id": 123,
  "first_name": "John",
  "last_name": "Doe",
  "city": "Seattle",
  "zip_code": "98101",
  "status": "ASSIGNED",
  "assigned_vetter_id": 2,
  "created_at": "2024-01-15T10:30:00",
  "updated_at": "2024-01-15T10:35:00"
}
```

**Response (no candidates):** `null`

### POST /api/v1/members/reclaim-stale

Manually reclaim stale assignments (admin only).

**Authentication:** Required (Super Admin role)

**Request:** Empty body

**Response:**
```json
{
  "reclaimed_count": 3,
  "message": "Successfully reclaimed 3 stale assignment(s)"
}
```

## Best Practices

### For Organizations

1. **Monitor Queue Depth**: Regularly check pending count to ensure candidates aren't backing up
2. **Review Audit Logs**: Check for frequent stale reclamations, which may indicate vetter capacity issues
3. **Adjust Threshold**: If candidates require extensive research, consider increasing `STALE_ASSIGNMENT_DAYS`
4. **Vetter Training**: Ensure vetters understand they'll be auto-assigned on login
5. **Manual Override**: Use manual assignment for urgent cases or specific vetter expertise

### For Vetters

1. **Login When Ready**: Don't login unless you're ready to review a candidate (you'll be auto-assigned)
2. **Complete Reviews**: Finish reviews promptly to get next candidate
3. **Use Notes**: Add detailed notes for other vetters who may need context
4. **Request Next**: Use "Get Next Candidate" if you have time for more

### For Admins

1. **Monitor Stale Assignments**: Periodically check Database tab for stale assignment counts
2. **Manual Reclamation**: Use manual reclamation button if you need to immediately free up stuck candidates
3. **Check Vetter Activity**: Review audit logs to identify inactive vetters
4. **Manual Assignment**: Reserve for special cases where specific vetter expertise is needed

## Troubleshooting

### No Candidates Being Assigned

**Symptom:** Vetter logs in but sees "No members assigned to you yet"

**Possible causes:**
1. No pending candidates in queue
2. All candidates are already assigned to other vetters
3. Database connection issue

**Solution:**
- Check pending count in admin Database tab
- Verify candidates exist with status=PENDING in database
- Check backend logs for errors

### Candidates Stuck in ASSIGNED

**Symptom:** Multiple candidates show ASSIGNED status for >7 days

**Possible causes:**
1. No vetters logging in to trigger reclamation
2. Stale reclamation code not running

**Solution:**
- Admin clicks "Reclaim Stale Assignments" button
- Check audit logs for STALE_CHECK actions
- Verify `updated_at` field is being updated properly

### Too Many Stale Reclamations

**Symptom:** Audit log shows frequent ASSIGNMENT_RECLAIMED actions

**Possible causes:**
1. Vetters not completing reviews within 7 days
2. Threshold too aggressive for your workflow
3. Vetter capacity issues

**Solution:**
- Increase `STALE_ASSIGNMENT_DAYS` threshold
- Review vetter workload and capacity
- Provide additional vetter training
- Consider adding more vetters

## Technical Implementation

### Database Schema Impact

No schema changes required. Uses existing fields:
- `status` - MemberStatus enum (PENDING, ASSIGNED, VETTED, REJECTED)
- `assigned_vetter_id` - Foreign key to users table
- `updated_at` - Timestamp for stale detection
- `created_at` - Timestamp for FIFO ordering

### Performance Considerations

**Query Optimization:**
- Status and assigned_vetter_id are indexed
- Queries are simple and efficient
- No N+1 query issues

**Stale Reclamation:**
- Runs synchronously during auto-assignment
- Typically affects 0-5 members
- Completes in <100ms

**Scaling:**
- System handles hundreds of concurrent vetters
- Queue depth can grow to thousands
- SQLite WAL mode prevents locking issues

### Security Considerations

**Vetter Isolation:**
- Vetters can only see their assigned members
- Cannot request specific member IDs
- Cannot see other vetters' assignments

**Admin Controls:**
- Only admins can manually reclaim stale assignments
- Only admins can manually assign to specific vetters
- All actions are audit logged

**Audit Trail:**
- Every assignment action is logged
- System actions use user_id=NULL
- Full traceability of all queue operations

## Future Enhancements

Potential improvements for future versions:

1. **Load Balancing**: Distribute candidates evenly across vetters based on current workload
2. **Priority Queue**: Allow marking certain candidates as urgent
3. **Vetter Preferences**: Allow vetters to specify areas of expertise for better matching
4. **Automated Reminders**: Email vetters about stale assignments before reclamation
5. **Metrics Dashboard**: Show average vetting time, queue depth trends, vetter performance
6. **Configurable Thresholds**: Allow admins to set stale threshold per-vetter or globally via UI
7. **Batch Assignment**: Assign multiple candidates at once to vetters who want higher throughput
