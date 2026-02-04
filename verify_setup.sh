#!/bin/bash

# Verification script for Signup Manager setup

echo "=========================================="
echo "Signup Manager - Setup Verification"
echo "=========================================="
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✓${NC} $1"
        return 0
    else
        echo -e "${RED}✗${NC} $1 (missing)"
        return 1
    fi
}

check_dir() {
    if [ -d "$1" ]; then
        echo -e "${GREEN}✓${NC} $1/"
        return 0
    else
        echo -e "${RED}✗${NC} $1/ (missing)"
        return 1
    fi
}

echo "Checking critical backend files..."
echo "-----------------------------------"
check_file "backend/requirements.txt"
check_file "backend/Dockerfile"
check_file "backend/app/main.py"
check_file "backend/app/config.py"
check_file "backend/app/database.py"
check_file "backend/app/dependencies.py"

echo ""
echo "Checking backend services..."
check_file "backend/app/services/encryption.py"
check_file "backend/app/services/auth.py"
check_file "backend/app/services/audit.py"
check_file "backend/app/services/blind_index.py"

echo ""
echo "Checking backend models..."
check_file "backend/app/models/user.py"
check_file "backend/app/models/member.py"
check_file "backend/app/models/audit_log.py"

echo ""
echo "Checking backend routers..."
check_file "backend/app/routers/auth.py"
check_file "backend/app/routers/public.py"
check_file "backend/app/routers/members.py"
check_file "backend/app/routers/users.py"

echo ""
echo "Checking backend tests..."
check_file "backend/tests/test_encryption.py"
check_file "backend/tests/test_auth.py"
check_file "backend/tests/test_vetter_isolation.py"

echo ""
echo "Checking frontend files..."
echo "-----------------------------------"
check_file "frontend/package.json"
check_file "frontend/Dockerfile"
check_file "frontend/vite.config.js"
check_file "frontend/tailwind.config.js"
check_file "frontend/index.html"

echo ""
echo "Checking frontend API layer..."
check_file "frontend/src/api/client.js"
check_file "frontend/src/api/auth.js"
check_file "frontend/src/api/members.js"
check_file "frontend/src/api/users.js"

echo ""
echo "Checking frontend pages..."
check_file "frontend/src/pages/Login.jsx"
check_file "frontend/src/pages/PublicApplicationForm.jsx"
check_file "frontend/src/pages/AdminDashboard.jsx"
check_file "frontend/src/pages/VetterDashboard.jsx"
check_file "frontend/src/pages/MemberDetailPage.jsx"

echo ""
echo "Checking frontend components..."
check_file "frontend/src/components/common/Button.jsx"
check_file "frontend/src/components/common/Input.jsx"
check_file "frontend/src/components/common/Select.jsx"
check_file "frontend/src/components/common/Modal.jsx"
check_file "frontend/src/components/layout/Header.jsx"
check_file "frontend/src/components/layout/ProtectedRoute.jsx"

echo ""
echo "Checking Docker configuration..."
echo "-----------------------------------"
check_file "docker-compose.yml"
check_file "docker-compose.dev.yml"
check_file ".env"
check_file ".env.example"
check_file ".gitignore"

echo ""
echo "Checking documentation..."
echo "-----------------------------------"
check_file "README.md"
check_file "QUICKSTART.md"
check_file "DEPLOYMENT_CHECKLIST.md"
check_file "IMPLEMENTATION_SUMMARY.md"
check_file "generate_keys.py"

echo ""
echo "Checking directories..."
echo "-----------------------------------"
check_dir "backend/app/models"
check_dir "backend/app/schemas"
check_dir "backend/app/services"
check_dir "backend/app/routers"
check_dir "backend/tests"
check_dir "frontend/src/api"
check_dir "frontend/src/components/common"
check_dir "frontend/src/components/layout"
check_dir "frontend/src/pages"
check_dir "local_data"

echo ""
echo "Checking .env configuration..."
echo "-----------------------------------"
if [ -f ".env" ]; then
    if grep -q "SECRET_KEY=" .env && grep -q "ENCRYPTION_KEY=" .env; then
        echo -e "${GREEN}✓${NC} .env file has required keys"
    else
        echo -e "${RED}✗${NC} .env file missing required keys"
    fi

    if grep -q "your-secret-key-here" .env || grep -q "your-fernet-key-here" .env; then
        echo -e "${YELLOW}⚠${NC} WARNING: .env appears to use example values - generate new keys!"
    else
        echo -e "${GREEN}✓${NC} .env appears to have custom keys"
    fi
else
    echo -e "${RED}✗${NC} .env file not found"
fi

echo ""
echo "=========================================="
echo "Verification Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Review any missing files above"
echo "2. Run: docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build"
echo "3. Test the application at http://localhost:5173"
echo "4. Run backend tests: cd backend && pytest tests/ -v"
echo ""
