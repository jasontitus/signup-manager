# Quick Start Guide

## Prerequisites

- Docker and Docker Compose installed
- Python 3.11+ (for running tests locally)
- Node.js 18+ (for frontend development)

## Quick Start (Development)

1. **Start the application**:
   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build
   ```

2. **Access the application**:
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

3. **Default Admin Credentials**:
   - Username: `admin`
   - Password: `AdminPassword123!`

## Testing the Application

### 1. Submit a Public Application

1. Go to http://localhost:5173/apply
2. Fill out the membership form
3. Submit the application

### 2. Login as Admin

1. Go to http://localhost:5173/login
2. Login with admin credentials
3. You'll be redirected to the Admin Dashboard

### 3. Admin Tasks

**Triage Tab**: Assign pending applications to vetters
- First, create a vetter user in the **Staff** tab
- Then assign applications from the **Triage** tab

**Database Tab**: View all members and their statuses

**Staff Tab**: Create and manage users (admins and vetters)

### 4. Login as Vetter

1. Create a vetter user from the Admin Staff tab
2. Logout and login with vetter credentials
3. View only assigned members
4. Click on a member to view details and decrypt PII
5. Add notes and update status

## Running Backend Tests

```bash
cd backend
pip install -r requirements.txt
pytest tests/ -v
```

Critical test to verify:
- `tests/test_vetter_isolation.py` - Ensures vetters can only access assigned members

## Generating New Keys

If you need to regenerate security keys:

```bash
python3 generate_keys.py
```

Copy the output to your `.env` file.

## Stopping the Application

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml down
```

To also remove volumes:
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml down -v
```

## Production Deployment

See [README.md](README.md) for full production deployment instructions.

## Common Issues

### Port Already in Use

If port 8000 or 5173 is already in use, you can change them in `docker-compose.dev.yml`.

### Database Locked

SQLite WAL mode is enabled. If you see "database locked" errors, ensure no other processes are accessing the database.

### Frontend Can't Connect to Backend

Check that:
1. Backend is running on port 8000
2. `VITE_API_URL` environment variable is set correctly
3. CORS is configured properly in backend

## Project Structure Overview

```
signup-manager/
├── backend/              # FastAPI backend
│   ├── app/
│   │   ├── models/      # Database models with encryption
│   │   ├── routers/     # API endpoints
│   │   └── services/    # Business logic (encryption, auth, audit)
│   └── tests/           # Backend tests
├── frontend/            # React frontend
│   └── src/
│       ├── api/         # API client
│       ├── components/  # Reusable UI components
│       └── pages/       # Page components
├── .env                 # Environment variables (DO NOT COMMIT)
└── docker-compose.yml   # Docker configuration
```

## Next Steps

1. Change the default admin password
2. Create vetter users
3. Test the complete workflow from application submission to vetting
4. Review audit logs in the database
5. Set up backups for the encryption key and database
