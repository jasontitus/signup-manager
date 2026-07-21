# Signup Manager

A secure membership application portal with strict role-based access control, field-level PII encryption, and Docker deployment.

> Looking for how to use the admin dashboard day-to-day (statuses, follow-ups, tags,
> CSV export) rather than how to set up or develop the app? See the
> [Staff Guide](STAFF_GUIDE.md).

## Features

- **Field-level PII Encryption**: Email, phone, and address encrypted at rest using Fernet symmetric encryption
- **Blind Index Search**: Email duplicate checking without decryption
- **Role-Based Access Control (RBAC)**:
  - Super Admin: Full access to all members and user management
  - Vetter: Access only to assigned members
- **Automated Vetting Queue**: Auto-assignment of candidates to vetters with stale assignment reclamation
- **Audit Logging**: All PII access is logged with user, timestamp, and action
- **CSV Export**: Admins can export members to CSV with a custom field selection and sort order
- **Public Application Form**: No authentication required for submitting applications
- **Docker Deployment**: Containerized for easy deployment to Raspberry Pi

## Tech Stack

- **Backend**: FastAPI (Python 3.11), SQLAlchemy, SQLite with WAL mode
- **Frontend**: React 18, Vite, Tailwind CSS, React Router
- **Security**: Fernet encryption, JWT authentication, bcrypt password hashing
- **Deployment**: Docker Compose

## Project Structure

```
signup-manager/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── models/         # SQLAlchemy models with encrypted fields
│   │   ├── schemas/        # Pydantic schemas
│   │   ├── services/       # Encryption, auth, audit services
│   │   ├── routers/        # API endpoints
│   │   └── utils/          # DB initialization
│   └── tests/              # Backend tests (encryption, auth, RBAC)
├── frontend/               # React frontend
│   └── src/
│       ├── api/            # API client with JWT interceptor
│       ├── components/     # Reusable components
│       ├── pages/          # Page components
│       └── context/        # Auth context
└── docker-compose.yml      # Production deployment
```

## Setup Instructions

### 1. Generate Security Keys

Run the following Python command to generate secure keys:

```bash
python3 generate_keys.py
```

This will output the required security keys. Copy them to your `.env` file.

### 2. Create Environment File

Copy `.env.example` to `.env` and fill in the generated keys:

```bash
cp .env.example .env
# Edit .env with your generated keys
```

### 3. Development Setup

`docker-compose.dev.yml` shares your `.env` for convenience, but always blanks out
`RESEND_API_KEY` and `NOTIFICATION_EMAIL` — manually testing the app locally (or running
the test suite) can never send a real email through your production Resend key. If you
need to test email sending itself, temporarily put a Resend sandbox key directly in
`docker-compose.dev.yml`'s `environment:` block (don't commit it).

Start the development environment:

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

This will start:
- Backend at http://localhost:8000
- Frontend at http://localhost:5173
- SQLite database in `./local_data/`

### 4. First Run Admin User

On first run, the system will create an admin user using the credentials from your `.env` file:
- Username: `FIRST_RUN_ADMIN_USER`
- Password: `FIRST_RUN_ADMIN_PASSWORD`

**IMPORTANT**: Change this password immediately after first login!

### 5. Production Deployment (Raspberry Pi)

1. Create the secure data directory on your Pi:
   ```bash
   sudo mkdir -p /mnt/secure_data
   sudo chown $USER:$USER /mnt/secure_data
   ```

2. Copy `.env` file to the Pi

3. Deploy using production compose:
   ```bash
   docker-compose up -d --build
   ```

This will:
- Backend available at http://pi-address:8000
- Frontend available at http://pi-address:80
- Data stored in `/mnt/secure_data/`

## API Documentation

Once running, visit:
- Interactive API docs: http://localhost:8000/docs
- ReDoc documentation: http://localhost:8000/redoc

## Usage

### Public Application Submission

Anyone can submit an application at `/apply` (no login required).

#### Customizing the Application Form

The form title, description, and custom fields are configured via `backend/data/form_config.json`. To customize the form for your instance without affecting the git repo, create a local override:

```bash
cp backend/data/form_config.json backend/data/form_config.local.json
# Edit form_config.local.json with your changes
```

The local file supports `title` and `description` fields at the top level:

```json
{
  "version": "1.0",
  "title": "Your Organization Membership",
  "description": "A welcome message shown below the title on the signup form.",
  "fields": [ ... ]
}
```

The `*.local.json` pattern is gitignored, so your instance-specific customizations stay local.

### Admin Workflow

1. Login at `/login`
2. View pending applications in the **Triage** tab
3. Manually assign applications to specific vetters (optional - auto-assignment handles this automatically)
4. Manage all members in the **Database** tab
   - Click "Reclaim Stale Assignments" to manually recover assignments from inactive vetters
   - Click "Export CSV" to download members as a CSV file
5. Manage users in the **Staff** tab

### CSV Export

Admins can export member data from the **Database** tab via the "Export CSV" button:

- **Field selection**: Choose which columns to include (name, email, phone, address, city, zip, status, tags, notes, applied/updated dates)
- **Sort options**: Sort by any field, ascending or descending
- **Filter aware**: The active status filter and archived toggle are applied to the export
- **Audited**: Every export is recorded in the audit log with the admin's username, the number of members exported, and the fields included

The endpoint (`GET /api/members/export`) is admin-only. PII is decrypted server-side at export time; handle downloaded files according to your data-handling policy.

### Vetter Workflow

1. Login at `/login` - **Automatically assigned the first pending candidate**
2. View assigned members in dashboard
3. Click on a member to view details (PII is decrypted and logged)
4. Add internal notes
5. Update member status (Vetted/Rejected) - **Automatically assigned next candidate**
6. Click "Get Next Candidate" button to manually request additional assignments

#### Auto-Assignment Features

- **On Login**: Vetters are automatically assigned the first pending candidate when they log in
- **On Completion**: When a vetter marks a candidate as VETTED or REJECTED, they're automatically assigned the next pending candidate
- **Manual Request**: Vetters can click "Get Next Candidate" at any time to request another assignment
- **FIFO Queue**: Candidates are assigned in order of application submission (oldest first)
- **Stale Assignment Reclamation**: Candidates assigned for more than 7 days are automatically returned to the pending queue

## Security Features

### PII Encryption

All sensitive fields are encrypted at rest:
- Email addresses
- Phone numbers
- Street addresses
- Occupational background
- Member connections
- Hoped impact

Encryption uses Fernet (AES-128 in CBC mode with HMAC authentication).

### Blind Index

Email addresses have a SHA256 blind index for duplicate checking without decryption:
- Salted hash of normalized email
- Enables duplicate detection
- Cannot be reversed to plaintext

### Vetter Isolation

Vetters can ONLY access members assigned to them:
- Query-level filtering enforces isolation
- API checks permissions before decrypting PII
- Attempting to access unassigned member returns 403 Forbidden

### Audit Logging

Every PII access and assignment action is logged:
- User who accessed
- Member accessed
- Action performed (VIEWED_PII, AUTO_ASSIGNED, ASSIGNMENT_RECLAIMED, etc.)
- Timestamp
- Details

View audit logs in the database `audit_logs` table.

### Network & Abuse Protections

- **Backend not directly exposed**: the backend only binds to `127.0.0.1:8000` on the host — all external traffic must go through the frontend nginx proxy, so it can't bypass the protections below.
- **Rate limiting**: nginx throttles `/api/auth/login`, `/unlock`, and `/api/public/apply` per IP. The backend additionally locks out an IP+username pair after 5 failed login/unlock attempts for 15 minutes.
- **Security headers & body size cap**: nginx sets `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`, and caps request bodies at 100kb.
- **Input bounds**: form fields, login credentials, and notes all have server-side length limits to prevent oversized payloads reaching encryption/storage.
- **CSV export injection guard**: exported cell values that start with `=`, `+`, `-`, `@`, tab, or CR are prefixed with `'` so Excel/Sheets can't execute them as formulas.
- **Startup secret validation**: the app refuses to start (direct mode) or unlock (vault mode) if `SECRET_KEY`, `ENCRYPTION_KEY`, or `EMAIL_BLIND_INDEX_SALT` are missing, instead of silently running with degraded security.

### Automated Queue Management

The system automatically manages the vetting queue to ensure candidates don't get stuck:

- **Auto-Assignment**: Vetters are automatically assigned candidates on login and after completing vetting
- **Stale Detection**: Assignments older than 7 days are automatically reclaimed
- **Queue Priority**: Candidates are assigned in FIFO order (oldest applications first)
- **Manual Override**: Admins can manually reclaim stale assignments or assign specific candidates to specific vetters

## Member Statuses & Follow-up Loop

Statuses: `PENDING` → `ASSIGNED` (being vetted) → `VETTED` / `REJECTED` / `NEEDS_FOLLOW_UP`, then
`IN_SIGNAL` (the "resting" status — member has been added to Signal), `DECLINED_SIGNAL` (signed up,
then decided against Signal), and the system-managed `ONE_MONTH_FOLLOWUP` / `SIX_MONTH_FOLLOWUP`.

### Status change notifications

- Marking a member **Vetted** or **Needs Follow-up** emails `VETTING_NOTIFICATION_EMAIL` with the member's name
- Bulk status changes send one digest email listing all affected names

### Follow-up pings (background scheduler, runs hourly)

- **One month after vetting**: member moves to `ONE_MONTH_FOLLOWUP` and `FOLLOWUP_NOTIFICATION_EMAIL` is emailed
- **Six months after entering In Signal**: member moves to `SIX_MONTH_FOLLOWUP` and `FOLLOWUP_NOTIFICATION_EMAIL` is emailed
- **Recurring loop**: after completing a follow-up, set the member back to **In Signal** — that restarts the
  six-month timer, so they resurface for a check-in every six months
- Multiple due members are batched into a single digest email per check
- Emails require `RESEND_API_KEY`; recipient addresses are configurable via
  `VETTING_NOTIFICATION_EMAIL` and `FOLLOWUP_NOTIFICATION_EMAIL` in `.env`

## Testing

Run backend tests:

```bash
cd backend
python -m pytest tests/
```

Critical tests:
- `test_encryption.py`: Encryption round-trip
- `test_auth.py`: Password hashing, JWT tokens
- `test_vetter_isolation.py`: **CRITICAL** - Ensures vetters cannot access other vetters' members

## Database Schema

### Users
- id, username, hashed_password, role, full_name, is_active

### Members
- id, first_name, last_name, city, zip_code
- **Encrypted**: _street_address, _phone_number, _email, _occupational_background, _know_member, _hoped_impact
- email_blind_index (for duplicate checking)
- status, assigned_vetter_id, notes

### Audit Logs
- id, user_id, member_id, action, details, timestamp

## Troubleshooting

### Database Locked Errors

SQLite WAL mode is enabled for better concurrency. If you still see locks:
- Ensure only one process is accessing the database
- Check file permissions on the database file

### Encryption Key Mismatch

If you see decryption errors:
- Ensure `ENCRYPTION_KEY` in `.env` matches the key used to encrypt data
- Never change the encryption key after data is encrypted
- Backup the encryption key securely!

### Port Conflicts

If ports 8000 or 5173 are in use:
- Change ports in `docker-compose.dev.yml`
- Update `VITE_API_URL` and `FRONTEND_URL` accordingly

## Backup Strategy

Critical data to backup:
1. **Encryption key** (`ENCRYPTION_KEY` in `.env`) - without this, data cannot be decrypted
2. **Database file** (`/mnt/secure_data/members.db`)
3. **Environment file** (`.env`)

## Security Considerations

- Store `.env` file securely (never commit to git)
- Rotate the JWT secret key periodically
- Use HTTPS in production
- Regularly review audit logs
- Implement rate limiting for login endpoint
- Consider database encryption at rest for additional security

## License

MIT License - see LICENSE file for details
