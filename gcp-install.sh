#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# Signup Manager - GCP Instance Installer
# ============================================================
# Installs and deploys the Signup Manager on a fresh GCP
# Compute Engine instance running Debian or Ubuntu.
#
# Usage:
#   chmod +x gcp-install.sh
#   sudo ./gcp-install.sh
#
# What this script does:
#   1. Installs Docker and Docker Compose
#   2. Creates an encrypted vault (secrets protected by master password)
#   3. Creates .env with non-secret config only
#   4. Sets up the data directory
#   5. Opens firewall ports (80, 443)
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
echo -e "${BOLD} Signup Manager - GCP Installer${NC}"
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
    # Get external IP for CORS
    EXTERNAL_IP=$(curl -sf -H "Metadata-Flavor: Google" \
        http://metadata.google.internal/computeMetadata/v1/instance/network-interfaces/0/access-configs/0/external-ip 2>/dev/null || echo "")

    FRONTEND_URL="http://localhost"
    if [ -n "$EXTERNAL_IP" ]; then
        FRONTEND_URL="http://${EXTERNAL_IP}"
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
    log ".env created (non-secret config only)."
fi

# ----------------------------------------------------------
# 6. Configure firewall
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
    warn "Ensure GCP firewall rules allow HTTP (80) and HTTPS (443)."
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

EXTERNAL_IP=$(curl -sf -H "Metadata-Flavor: Google" \
    http://metadata.google.internal/computeMetadata/v1/instance/network-interfaces/0/access-configs/0/external-ip 2>/dev/null || echo "")

if [ -n "$EXTERNAL_IP" ]; then
    echo -e "  Unlock page:  ${BOLD}http://${EXTERNAL_IP}/unlock${NC}"
    echo -e "  Frontend:     ${BOLD}http://${EXTERNAL_IP}${NC}  (after unlock)"
else
    echo -e "  Unlock page:  ${BOLD}http://<YOUR-INSTANCE-IP>/unlock${NC}"
    echo -e "  Frontend:     ${BOLD}http://<YOUR-INSTANCE-IP>${NC}  (after unlock)"
fi

echo ""
echo -e "${BOLD}How it works:${NC}"
echo "  1. Visit the unlock page and enter your master password"
echo "  2. Secrets are decrypted into memory — never written to disk"
echo "  3. The app starts and you can log in normally"
echo "  4. On reboot/restart, visit /unlock again to re-enter the password"
echo ""
echo -e "${BOLD}GCP Firewall Reminder:${NC}"
echo "  Ensure your VPC firewall allows ingress on port 80 (HTTP)."
echo "  gcloud compute firewall-rules create allow-http \\"
echo "    --allow tcp:80 --target-tags http-server"
echo ""
