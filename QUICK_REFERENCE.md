# Quick Reference Card

## 🚀 Quick Start

```bash
# Start development
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build

# Access
Frontend: http://localhost:5173
Backend:  http://localhost:8000
API Docs: http://localhost:8000/docs

# Login
Username: admin
Password: AdminPassword123!
```

## 📁 Key Files

| File | Purpose |
|------|---------|
| `.env` | **BACKUP THIS!** Contains encryption key |
| `backend/app/services/encryption.py` | PII encryption logic |
| `backend/app/routers/members.py` | Vetter isolation enforcement |
| `backend/tests/test_vetter_isolation.py` | **CRITICAL** security test |
| `docker-compose.yml` | Production deployment |
| `docker-compose.dev.yml` | Development overrides |

## 🔐 Security Keys

```bash
# Generate new keys
python3 generate_keys.py

# Copy output to .env file
# NEVER commit .env to git!
```

## 🧪 Testing

```bash
# Verify setup
./verify_setup.sh

# Run backend tests
cd backend
pip install -r requirements.txt
pytest tests/ -v

# Critical test (vetter isolation)
pytest tests/test_vetter_isolation.py -v
```

## 🔍 Debugging

```bash
# View logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Access database
docker-compose exec backend sqlite3 /app/data/members.db

# Check encrypted data
SELECT id, first_name, _email FROM members;

# Check audit logs
SELECT * FROM audit_logs ORDER BY timestamp DESC;

# Check container status
docker-compose ps
```

## 🎯 User Roles

| Role | Access | Routes |
|------|--------|--------|
| **Public** | Submit applications only | `/apply` |
| **VETTER** | View/edit assigned members only | `/vetter`, `/members/:id` |
| **SUPER_ADMIN** | Full access to all members + user management | `/admin`, `/members/:id` |

## 📊 Database Tables

```sql
-- Check users
SELECT id, username, role FROM users;

-- Check members (encrypted)
SELECT id, first_name, last_name, status, assigned_vetter_id FROM members;

-- Check audit log
SELECT user_id, member_id, action, timestamp FROM audit_logs;
```

## 🛠️ Common Tasks

### Create a Vetter
1. Login as admin
2. Go to "Staff" tab
3. Click "Add User"
4. Set role to "Vetter"

### Assign Application
1. Login as admin
2. Go to "Triage" tab
3. Click "Assign to Vetter"
4. Select vetter from dropdown

### View Member Details
1. Login (admin or vetter)
2. Click on member card
3. PII automatically decrypted and logged

### Add Internal Note
1. On member detail page
2. Scroll to "Internal Notes"
3. Type note and click "Add Note"

## 🚨 Emergency Commands

```bash
# Stop everything
docker-compose -f docker-compose.yml -f docker-compose.dev.yml down

# Reset database (CAUTION: deletes all data)
rm -rf local_data/*
docker-compose up --build

# View container errors
docker-compose logs backend | grep -i error

# Restart single service
docker-compose restart backend
```

## 📋 API Endpoints Quick Reference

### Public
- `POST /api/v1/public/apply` - Submit application

### Auth
- `POST /api/v1/auth/login` - Login (returns JWT)

### Members
- `GET /api/v1/members` - List (filtered by role)
- `GET /api/v1/members/{id}` - Get with PII
- `PATCH /api/v1/members/{id}/assign` - Assign to vetter
- `PATCH /api/v1/members/{id}/status` - Update status
- `POST /api/v1/members/{id}/notes` - Add note

### Users (Admin Only)
- `GET /api/v1/users` - List all
- `POST /api/v1/users` - Create
- `PATCH /api/v1/users/{id}` - Update
- `DELETE /api/v1/users/{id}` - Delete

## 🔒 Security Checklist

- [ ] Changed default admin password
- [ ] Generated unique encryption keys
- [ ] Backed up `.env` file
- [ ] `.env` not committed to git
- [ ] Ran vetter isolation tests
- [ ] Verified PII encryption in database
- [ ] Checked audit logs working

## 📚 Documentation

| Doc | Purpose |
|-----|---------|
| **README.md** | Full documentation |
| **QUICKSTART.md** | Getting started guide |
| **TEST_SCENARIOS.md** | 15 test scenarios |
| **DEPLOYMENT_CHECKLIST.md** | Production deployment |
| **STATUS.md** | Current project status |
| **SPEC.md** | Original specification |

## 🐛 Common Issues

| Problem | Solution |
|---------|----------|
| Port 8000 in use | Change in `docker-compose.dev.yml` |
| Database locked | Stop containers, delete `.db-wal` files |
| Frontend can't connect | Check backend running, CORS configured |
| Encryption error | Verify `ENCRYPTION_KEY` in `.env` |
| 403 on member access | Check vetter assignment |

## 🎓 Test Workflow

1. ✅ Submit application (public form)
2. ✅ Login as admin
3. ✅ Create vetter user
4. ✅ Assign application to vetter
5. ✅ Login as vetter
6. ✅ View member (verify PII decrypted)
7. ✅ Add note
8. ✅ Update status to "VETTED"
9. ✅ Test vetter isolation (try to access other vetter's member)
10. ✅ Check audit logs in database

## 📞 Quick Support

```bash
# Check all files present
./verify_setup.sh

# View API documentation
open http://localhost:8000/docs

# Access frontend
open http://localhost:5173

# Check database contents
docker-compose exec backend sqlite3 /app/data/members.db ".schema"
```

---

**Most Important**:
1. **Backup encryption key** (in `.env`)
2. **Test vetter isolation** (Scenario 9)
3. **Change default password**
