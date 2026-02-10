# CSV Import Tool

This tool allows you to bulk import member signups from a CSV file into the Signup Manager database.

## Features

- Import multiple signups from a CSV file
- Automatically encrypts PII fields (email, phone, street address)
- Generates email blind indexes for duplicate detection
- Handles custom fields dynamically
- Option to mark imports as pre-vetted or pending
- Duplicate email detection
- Detailed error reporting

## Usage

### Basic Import (as PENDING)

Import signups that need vetting:

```bash
cd backend
python import_csv.py ../example.csv
```

### Import as Pre-Vetted

Import signups that have already been vetted:

```bash
python import_csv.py ../example.csv --vetted
```

### Import with Assigned Vetter

Import as vetted and assign to a specific vetter (User ID 1):

```bash
python import_csv.py ../example.csv --vetted --user-id 1
```

## CSV Format

The CSV file should have the following columns:

| Column Name | Required | Description |
|------------|----------|-------------|
| Name | Yes | Full name (will be split into first/last name) |
| Street address | No | Street address (encrypted) |
| City | Yes | City name |
| Zip code | Yes | ZIP code |
| Phone number | No | Phone number (encrypted) |
| Email address (for newsletter) | No | Email address (encrypted) |
| Where did you learn about IPA+? | No | Custom field |
| What personal talent, skill, experience, or superpower do you bring to the group? | No | Custom field |
| What is your occupational background? ... | No | Custom field |
| Do you know someone who is a member of IPA+? If so, who? | No | Custom field |
| What impact do you hope to have by joining IPA+? ... | No | Custom field |
| Timestamp | No | Original submission timestamp (stored in custom fields) |

## How It Works

1. **Name Parsing**: Splits the "Name" field into first and last name
   - "John Doe" → first_name: "John", last_name: "Doe"
   - "Mary Jane Smith" → first_name: "Mary", last_name: "Jane Smith"

2. **Duplicate Detection**: Checks email blind index to prevent duplicate imports
   - Skips rows where email already exists
   - Reports skipped rows in the output

3. **Encryption**: Automatically encrypts sensitive fields:
   - Email address
   - Phone number
   - Street address
   - Custom fields (stored as encrypted JSON)

4. **Custom Fields**: Maps CSV columns to custom fields JSON:
   - `where_learn`: Where they learned about the organization
   - `superpower`: Personal talents/skills
   - `occupational_background`: Job/career background
   - `know_member`: Known members
   - `hoped_impact`: Expected impact
   - `original_timestamp`: Original CSV timestamp

5. **Audit Trail**: Creates audit log entries for each import

## Docker Environment

If running in Docker, use docker-compose:

```bash
docker-compose exec backend python import_csv.py /app/example.csv --vetted
```

Or copy your CSV into the container first:

```bash
docker cp mydata.csv signup-manager-backend-1:/app/mydata.csv
docker-compose exec backend python import_csv.py /app/mydata.csv
```

## Output

The script provides detailed output:

```
Importing from: example.csv
Status: PENDING

==================================================
Import Complete
==================================================
Total rows processed: 10
Successfully imported: 8
Skipped/Errors: 2

Errors/Warnings:
  - Row 5: Empty name field
  - Row 8: Email already exists (Member ID: 12)
```

## Exit Codes

- `0`: All records imported successfully
- `1`: Some records were skipped or had errors (but successful records were still imported)

## Notes

- The script commits changes only after all rows are processed successfully
- If a fatal error occurs, all changes are rolled back
- Duplicate emails are detected before import using the blind index
- Empty name fields will skip the row
- All PII is automatically encrypted using the system's encryption key
