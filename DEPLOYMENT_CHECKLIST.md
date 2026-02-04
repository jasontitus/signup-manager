# Deployment Checklist

## Pre-Deployment Security Review

- [ ] Generated unique security keys (not using example values)
- [ ] `.env` file is NOT committed to git
- [ ] `.gitignore` includes `.env` and `local_data/`
- [ ] Changed `FIRST_RUN_ADMIN_PASSWORD` from default
- [ ] Backed up encryption key to secure location
- [ ] Reviewed all TODO/FIXME comments in code

## Raspberry Pi Setup

### 1. System Preparation

- [ ] Raspberry Pi OS installed and updated
- [ ] Docker and Docker Compose installed
- [ ] Sufficient storage available (recommend 32GB+ SD card)
- [ ] Static IP configured (optional but recommended)

### 2. Data Directory Setup

```bash
# Create secure data directory
sudo mkdir -p /mnt/secure_data
sudo chown $USER:$USER /mnt/secure_data
sudo chmod 700 /mnt/secure_data
```

- [ ] Created `/mnt/secure_data` directory
- [ ] Set proper permissions (700)
- [ ] Verified disk space available

### 3. Transfer Files

```bash
# On your Mac, from the project directory
scp -r . pi@raspberry-pi-ip:~/signup-manager/

# Or use rsync
rsync -av --exclude 'local_data' --exclude '.git' \
  . pi@raspberry-pi-ip:~/signup-manager/
```

- [ ] Transferred project files to Pi
- [ ] Transferred `.env` file securely
- [ ] Verified all files copied correctly

### 4. Build and Deploy

```bash
# SSH into the Pi
ssh pi@raspberry-pi-ip

# Navigate to project
cd ~/signup-manager

# Build and start containers
docker-compose up -d --build
```

- [ ] Built Docker images successfully
- [ ] Containers started without errors
- [ ] Backend healthcheck passing
- [ ] Frontend accessible

### 5. Verify Deployment

```bash
# Check container status
docker-compose ps

# View backend logs
docker-compose logs backend

# View frontend logs
docker-compose logs frontend

# Test health endpoint
curl http://localhost:8000/api/v1/health
```

- [ ] All containers running
- [ ] No errors in logs
- [ ] Health endpoint returns `{"status": "healthy"}`
- [ ] Database created in `/mnt/secure_data/members.db`
- [ ] First admin user created

### 6. Test Access

- [ ] Frontend accessible at `http://pi-ip:80`
- [ ] Backend API accessible at `http://pi-ip:8000`
- [ ] API docs accessible at `http://pi-ip:8000/docs`
- [ ] Can login with admin credentials
- [ ] Can submit public application
- [ ] Can create vetter user
- [ ] Can assign application to vetter

### 7. Security Hardening (Recommended)

- [ ] Configure firewall (ufw) to allow only necessary ports
- [ ] Set up HTTPS with Let's Encrypt (if exposing to internet)
- [ ] Change default admin password after first login
- [ ] Disable password authentication for SSH
- [ ] Set up automatic security updates
- [ ] Configure fail2ban for brute force protection

## Post-Deployment

### Backup Strategy

- [ ] Backup encryption key to secure offline storage
- [ ] Set up automated database backups
- [ ] Document backup restoration procedure
- [ ] Test backup restoration process

### Monitoring

- [ ] Set up container monitoring (Portainer, etc.)
- [ ] Configure log rotation
- [ ] Set up disk space alerts
- [ ] Monitor audit logs regularly

### Maintenance

- [ ] Schedule regular updates (docker pull, rebuild)
- [ ] Review audit logs weekly
- [ ] Rotate JWT secret key quarterly
- [ ] Review and prune old audit logs

## Troubleshooting

### Container Won't Start

```bash
# View detailed logs
docker-compose logs -f backend

# Check environment variables
docker-compose exec backend env | grep -E "SECRET_KEY|DATABASE_URL"

# Verify volume mounts
docker-compose exec backend ls -la /app/data
```

### Database Issues

```bash
# Access database
docker-compose exec backend sqlite3 /app/data/members.db

# Check tables
.tables

# Check admin user
SELECT username, role FROM users;
```

### Frontend Can't Connect to Backend

- Check CORS configuration in backend
- Verify `VITE_API_URL` in frontend build
- Check network connectivity between containers
- Review nginx configuration

### Encryption Errors

- Verify `ENCRYPTION_KEY` matches the key used to encrypt existing data
- Check for key mismatch errors in logs
- If key is lost, encrypted data cannot be recovered

## Rollback Plan

If deployment fails:

```bash
# Stop containers
docker-compose down

# Restore from backup
sudo cp /backup/members.db /mnt/secure_data/members.db

# Restart with previous version
git checkout <previous-tag>
docker-compose up -d --build
```

## Production URLs (Update After Deployment)

- Frontend: http://[PI_IP_ADDRESS]:80
- Backend API: http://[PI_IP_ADDRESS]:8000
- API Documentation: http://[PI_IP_ADDRESS]:8000/docs

## Support Contacts

- System Admin: [YOUR_EMAIL]
- Technical Support: [SUPPORT_EMAIL]
- Emergency Contact: [EMERGENCY_CONTACT]

---

**Deployment Date**: _______________
**Deployed By**: _______________
**Version**: 1.0.0
**Notes**:
