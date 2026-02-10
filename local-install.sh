#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# Signup Manager - Local Server Installer
# ============================================================
# Installs and deploys the Signup Manager on a local Linux
# server (home server, Raspberry Pi, mini PC, etc.) running
# Debian or Ubuntu.
#
# Usage:
#   chmod +x local-install.sh
#   sudo ./local-install.sh
#
# What this script does:
#   1. Installs Docker and Docker Compose
#   2. Creates an encrypted vault (secrets protected by master password)
#   3. Creates .env with non-secret config only
#   4. Sets up the data directory
#   5. Optionally configures firewall
#   6. Builds and starts containers
#   7. Installs a systemd service for auto-start on boot
#
# After install, visit http://<IP>/unlock and enter your
# master password to start the application.
# ============================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m'

log()  { echo -e "${GREEN}[+]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
err()  { echo -e "${RED}[x]${NC} $1"; exit 1; }

# ----------------------------------------------------------
# Pre-flight checks
# ----------------------------------------------------------
if [[ $EUID -ne 0 ]]; then
    err "This script must be run as root (use sudo)."
fi

# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS_ID="${ID}"
else
    err "Cannot detect OS. This script supports Debian and Ubuntu."
fi

case "$OS_ID" in
    debian|ubuntu) ;;
    *) err "Unsupported OS: $OS_ID. This script supports Debian and Ubuntu." ;;
esac

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo -e "${BOLD}=========================================${NC}"
echo -e "${BOLD} Signup Manager - Local Server Installer${NC}"
echo -e "${BOLD}=========================================${NC}"
echo ""

# ----------------------------------------------------------
# 1. Install Docker
# ----------------------------------------------------------
if command -v docker &>/dev/null; then
    log "Docker already installed: $(docker --version)"
else
    log "Installing Docker..."
    apt-get update -qq
    apt-get install -y -qq ca-certificates curl gnupg lsb-release >/dev/null

    install -m 0755 -d /etc/apt/keyrings
    if [ "$OS_ID" = "ubuntu" ]; then
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg 2>/dev/null
        chmod a+r /etc/apt/keyrings/docker.gpg
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" > /etc/apt/sources.list.d/docker.list
    else
        curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg 2>/dev/null
        chmod a+r /etc/apt/keyrings/docker.gpg
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" > /etc/apt/sources.list.d/docker.list
    fi

    apt-get update -qq
    apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin >/dev/null
    systemctl enable docker
    systemctl start docker
    log "Docker installed: $(docker --version)"
fi

# Add the calling user to docker group (if run via sudo)
if [ -n "${SUDO_USER:-}" ]; then
    usermod -aG docker "$SUDO_USER" 2>/dev/null || true
fi

# ----------------------------------------------------------
# 2. Install Python + cryptography (needed for vault)
# ----------------------------------------------------------
if ! command -v python3 &>/dev/null; then
    log "Installing Python 3..."
    apt-get install -y -qq python3 python3-pip >/dev/null
fi

python3 -c "from cryptography.fernet import Fernet" 2>/dev/null || {
    log "Installing cryptography library..."
    pip3 install -q cryptography 2>/dev/null || \
        apt-get install -y -qq python3-cryptography >/dev/null
}

# ----------------------------------------------------------
# 3. Set up data directory
# ----------------------------------------------------------
DATA_DIR="/mnt/secure_data"
if [ ! -d "$DATA_DIR" ]; then
    log "Creating data directory at $DATA_DIR..."
    mkdir -p "$DATA_DIR"
fi
chmod 700 "$DATA_DIR"

if [ -n "${SUDO_USER:-}" ]; then
    chown "$SUDO_USER":"$SUDO_USER" "$DATA_DIR"
fi

log "Data directory ready: $DATA_DIR"

# ----------------------------------------------------------
# 4. Create encrypted vault
# ----------------------------------------------------------
VAULT_PATH="$DATA_DIR/.vault"
if [ -f "$VAULT_PATH" ]; then
    warn "Vault already exists at $VAULT_PATH — skipping creation."
    warn "To recreate, delete it and re-run this script."
else
    log "Creating encrypted vault..."
    echo ""
    echo -e "${BOLD}The vault encrypts all secrets with a master password.${NC}"
    echo -e "${BOLD}You will enter this password each time the app starts.${NC}"
    echo ""
    python3 "$SCRIPT_DIR/vault.py" create --file "$VAULT_PATH"
    chmod 600 "$VAULT_PATH"
    log "Vault created at $VAULT_PATH"
fi

# ----------------------------------------------------------
# 5. Create .env (non-secret config only)
# ----------------------------------------------------------
if [ -f "$SCRIPT_DIR/.env" ]; then
    warn ".env already exists — skipping."
else
    # Detect local IP for CORS
    LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "")

    FRONTEND_URL="http://localhost"
    if [ -n "$LOCAL_IP" ]; then
        FRONTEND_URL="http://${LOCAL_IP}"
    fi

    cat > "$SCRIPT_DIR/.env" <<EOF
# Non-secret configuration (secrets are in the encrypted vault)
DATABASE_URL=sqlite:////app/data/members.db
FRONTEND_URL=${FRONTEND_URL}
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=480
VAULT_FILE=/app/data/.vault
EOF

    chmod 644 "$SCRIPT_DIR/.env"
    log ".env created with FRONTEND_URL=${FRONTEND_URL}"
fi

# ----------------------------------------------------------
# 6. Configure firewall (optional)
# ----------------------------------------------------------
if command -v ufw &>/dev/null; then
    log "Configuring firewall (ufw)..."
    ufw allow 22/tcp  >/dev/null 2>&1 || true
    ufw allow 80/tcp  >/dev/null 2>&1 || true
    ufw allow 443/tcp >/dev/null 2>&1 || true
    ufw --force enable >/dev/null 2>&1 || true
    log "Firewall configured (ports 22, 80, 443 open)."
else
    warn "ufw not found — skipping firewall setup."
    warn "If you have a firewall, allow ports 80 (HTTP) and 443 (HTTPS)."
fi

# ----------------------------------------------------------
# 7. Build and deploy
# ----------------------------------------------------------
log "Building and starting containers (this may take a few minutes)..."
cd "$SCRIPT_DIR"
docker compose up -d --build

# ----------------------------------------------------------
# 8. Set up systemd service for auto-start
# ----------------------------------------------------------
SERVICE_FILE="/etc/systemd/system/signup-manager.service"
if [ ! -f "$SERVICE_FILE" ]; then
    log "Installing systemd service for auto-start on boot..."
    cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=Signup Manager Application
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=${SCRIPT_DIR}
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable signup-manager.service
    log "Systemd service installed and enabled."
fi

# ----------------------------------------------------------
# 9. Verify deployment
# ----------------------------------------------------------
log "Waiting for services to start..."
sleep 5

RESPONDING=false
for i in 1 2 3 4 5 6; do
    if curl -sf http://localhost:8000/api/health >/dev/null 2>&1; then
        RESPONDING=true
        break
    fi
    sleep 5
done

# Detect local IP again for final output
LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "")

echo ""
echo -e "${BOLD}=========================================${NC}"
if $RESPONDING; then
    echo -e "${GREEN}${BOLD} Deployment successful!${NC}"
else
    echo -e "${YELLOW}${BOLD} Containers started (waiting for response)${NC}"
    echo -e "  Run: docker compose logs -f"
fi
echo -e "${BOLD}=========================================${NC}"
echo ""

if [ -n "$LOCAL_IP" ]; then
    echo -e "  Unlock page:  ${BOLD}http://${LOCAL_IP}/unlock${NC}"
    echo -e "  Unlock page:  ${BOLD}http://localhost/unlock${NC}  (from this machine)"
    echo -e "  Frontend:     ${BOLD}http://${LOCAL_IP}${NC}  (after unlock)"
else
    echo -e "  Unlock page:  ${BOLD}http://localhost/unlock${NC}"
    echo -e "  Frontend:     ${BOLD}http://localhost${NC}  (after unlock)"
fi

echo ""
echo -e "${BOLD}How it works:${NC}"
echo "  1. Visit the unlock page and enter your master password"
echo "  2. Secrets are decrypted into memory — never written to disk"
echo "  3. The app starts and you can log in normally"
echo "  4. On reboot/restart, visit /unlock again to re-enter the password"
echo ""
