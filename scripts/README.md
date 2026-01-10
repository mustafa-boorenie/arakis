# Arakis Automation Scripts

This directory contains automation scripts for deployment, rollback, and maintenance operations.

## Scripts Overview

### Deployment Scripts

#### `deploy.sh`
Automated deployment script with zero-downtime strategy.

**Features:**
- Pre-deployment health checks
- Automatic backup before deployment
- Git code updates
- Docker image pulls
- Database migrations
- Rolling updates
- Post-deployment verification
- Comprehensive health checks
- Automatic cleanup

**Usage:**
```bash
# Deploy latest code
sudo ./deploy.sh

# Deploy specific commit
sudo ./deploy.sh abc1234
```

**Requirements:**
- Must run as root/sudo
- Minimum 5GB free disk space
- Docker daemon running
- .env file configured

**Process:**
1. Pre-deployment checks (Docker, disk space, .env)
2. Save current state for rollback
3. Update application code
4. Pull new Docker images
5. Run database migrations
6. Rolling update of services
7. Health checks
8. Cleanup old images
9. Tag successful deployment

**Duration:** 2-5 minutes

---

#### `rollback.sh`
Automated rollback script for failed deployments.

**Features:**
- Automatic rollback to last known good state
- Database restore from backup
- Code revert
- Docker image rollback
- Service restart
- Health verification

**Usage:**
```bash
# Rollback to last deployment (with DB restore)
sudo ./rollback.sh

# Rollback to specific commit
sudo ./rollback.sh --commit abc1234

# Rollback code only (skip database)
sudo ./rollback.sh --skip-db
```

**Options:**
- `--skip-db` - Skip database rollback
- `--commit SHA` - Rollback to specific commit

**Process:**
1. Confirm rollback operation
2. Determine rollback target
3. Stop services
4. Restore database from backup (optional)
5. Revert code to previous commit
6. Rebuild Docker images
7. Start services
8. Health checks
9. Log rollback details

**Duration:** 3-7 minutes (depending on database size)

**Warning:** Rollback is a destructive operation. Always verify backups before rolling back.

---

## Script Locations

When deployed to production VM:

- `/opt/arakis/scripts/deploy.sh` - Deployment script
- `/opt/arakis/scripts/rollback.sh` - Rollback script
- `/opt/arakis/deploy/backup.sh` - Backup script
- `/opt/arakis/deploy/health_check.sh` - Health check script

## Logs

All scripts log to:
- **Deployment:** `/var/log/arakis-deploy.log`
- **Rollback:** `/var/log/arakis-rollback.log`
- **Backups:** `/var/log/arakis-backup.log`
- **systemd:** `journalctl -u arakis`

## CI/CD Integration

These scripts are automatically executed by GitHub Actions workflows:

- **CI Workflow** (`.github/workflows/ci.yml`)
  - Runs tests on PRs
  - Lints code
  - Security scans
  - Integration tests

- **Docker Build** (`.github/workflows/docker-build.yml`)
  - Builds Docker images
  - Pushes to GitHub Container Registry
  - Scans for vulnerabilities
  - Multi-architecture builds

- **CD Workflow** (`.github/workflows/cd.yml`)
  - Automated deployment on merge to main
  - Calls `deploy.sh` via SSH
  - Runs `health_check.sh` for verification
  - Calls `rollback.sh` on failure

## Manual Deployment Process

### Step 1: Pre-Deployment

```bash
# SSH to server
ssh deploy-user@your-server.com

# Check current status
cd /opt/arakis
sudo ./deploy/health_check.sh --verbose

# Create manual backup
sudo ./deploy/backup.sh
```

### Step 2: Deploy

```bash
# Run deployment
sudo ./scripts/deploy.sh

# Monitor logs
tail -f /var/log/arakis-deploy.log
```

### Step 3: Verify

```bash
# Check health
curl https://your-domain.com/health

# View API docs
open https://your-domain.com/docs

# Check logs
docker logs -f arakis-api
```

### Step 4: If Deployment Fails

```bash
# Automatic rollback (if CD workflow is running)
# OR manual rollback:
sudo ./scripts/rollback.sh

# Check status
sudo ./deploy/health_check.sh --verbose
```

## Rollback Process

### When to Rollback

Rollback when:
- Health checks fail after deployment
- API returns errors
- Database migrations fail
- Services won't start
- Critical functionality broken

### How to Rollback

**Option 1: Automatic (via CI/CD)**
- CD workflow automatically rolls back on failed health checks
- No manual intervention needed

**Option 2: Manual**
```bash
# SSH to server
ssh deploy-user@your-server.com

# Run rollback
cd /opt/arakis
sudo ./scripts/rollback.sh

# Verify rollback
curl https://your-domain.com/health
sudo ./deploy/health_check.sh
```

### After Rollback

1. Investigate root cause
2. Review logs: `/var/log/arakis-deploy.log`
3. Check container logs: `docker logs arakis-api`
4. Fix issues locally
5. Test fixes in development
6. Deploy again when ready

## Troubleshooting

### Deployment Script Fails

**Issue:** Pre-deployment checks fail
```bash
# Check disk space
df -h /opt/arakis

# Check Docker
sudo systemctl status docker

# Check .env file
sudo ls -l /opt/arakis/.env
```

**Issue:** Database migrations fail
```bash
# Check PostgreSQL
docker logs arakis-postgres

# Check migration status
docker compose exec api alembic current
docker compose exec api alembic history
```

**Issue:** Health checks fail
```bash
# Detailed health check
sudo /opt/arakis/deploy/health_check.sh --verbose

# Check API logs
docker logs arakis-api --tail 100

# Check service status
docker compose ps
```

### Rollback Script Fails

**Issue:** No backup found
```bash
# List backups
ls -lh /var/backups/arakis/

# Create emergency backup
sudo /opt/arakis/deploy/backup.sh
```

**Issue:** Database restore fails
```bash
# Check backup integrity
gunzip -t /var/backups/arakis/arakis_backup_*.sql.gz

# Manual restore
gunzip -c /var/backups/arakis/backup.sql.gz | \
  docker compose exec -T postgres psql -U arakis -d arakis
```

**Issue:** Git conflicts
```bash
# Reset to clean state
cd /opt/arakis
git reset --hard HEAD
git clean -fd
```

## Best Practices

### Before Deployment

1. **Test locally** - Always test changes with `docker compose up`
2. **Run tests** - `pytest tests/` should pass
3. **Check CI** - Wait for CI workflow to pass
4. **Backup** - Verify recent backup exists
5. **Notify team** - Let team know about deployment
6. **Low traffic** - Deploy during low-traffic periods

### During Deployment

1. **Monitor logs** - Watch deployment logs in real-time
2. **Check health** - Verify health checks pass
3. **Test API** - Hit a few endpoints manually
4. **Watch metrics** - Monitor CPU, memory, errors
5. **Stay available** - Be ready to rollback if needed

### After Deployment

1. **Verify functionality** - Test critical features
2. **Monitor for errors** - Check logs for 15-30 minutes
3. **Check metrics** - Ensure no performance degradation
4. **Update docs** - Document any changes
5. **Post-mortem** - If issues occurred, document learnings

## Security Considerations

### SSH Keys

- Deploy uses SSH key authentication
- Store private key as GitHub secret: `DEPLOY_SSH_KEY`
- Never commit private keys to repository
- Use separate deploy user with limited permissions

### Secrets Management

- Environment variables stored in `.env`
- `.env` file permissions: 600 (owner read/write only)
- GitHub secrets for CI/CD credentials
- Rotate secrets periodically

### Access Control

- Deployment scripts require root/sudo
- Use dedicated deploy user (not root)
- Limit SSH access to deployment hosts
- Audit deployment logs regularly

## Monitoring

### Deployment Metrics

Track:
- Deployment frequency
- Deployment duration
- Success/failure rate
- Rollback frequency
- Time to recovery

### Tools

- GitHub Actions for CI/CD status
- Health check script for system status
- Docker stats for resource usage
- Application logs for errors

## Support

- **Documentation:** `/opt/arakis/deploy/README.md`
- **Health Checks:** `./deploy/health_check.sh --verbose`
- **Logs:** `/var/log/arakis-*.log`
- **GitHub Issues:** Report bugs and feature requests

## Quick Reference

```bash
# Deploy
sudo ./scripts/deploy.sh

# Deploy specific commit
sudo ./scripts/deploy.sh abc1234

# Rollback
sudo ./scripts/rollback.sh

# Rollback to specific commit
sudo ./scripts/rollback.sh --commit abc1234

# Rollback without DB
sudo ./scripts/rollback.sh --skip-db

# Backup
sudo ./deploy/backup.sh

# Health check
sudo ./deploy/health_check.sh --verbose

# View logs
sudo journalctl -u arakis -f
docker logs -f arakis-api

# Check status
docker compose ps
docker stats
```
