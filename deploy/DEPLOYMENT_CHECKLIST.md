# Arakis Deployment Checklist

Use this checklist when deploying Arakis to a production server.

## Pre-Deployment

### Requirements
- [ ] Ubuntu 22.04 LTS server provisioned
- [ ] Server has minimum 2GB RAM, 2 CPU cores
- [ ] Server has at least 20GB free disk space
- [ ] Domain name registered
- [ ] DNS A record pointing to server IP
- [ ] SSH access to server configured
- [ ] Server IP whitelisted in firewall (if applicable)

### Credentials
- [ ] OpenAI API key obtained
- [ ] Email address for Unpaywall API
- [ ] Email address for SSL certificates
- [ ] GitHub repository accessible (if private, deploy key added)

## Deployment Steps

### 1. Initial Server Setup
- [ ] SSH into server
- [ ] Update system: `sudo apt update && sudo apt upgrade -y`
- [ ] Verify DNS: `dig your-domain.com` shows correct IP
- [ ] Download setup script or clone repository

### 2. Run Automated Setup
- [ ] Execute: `sudo bash setup_vm.sh <domain> <email> [repo-url]`
- [ ] Verify no errors during installation
- [ ] Confirm all services installed:
  - [ ] Docker
  - [ ] Docker Compose
  - [ ] Nginx
  - [ ] Certbot
  - [ ] UFW firewall

### 3. Configure Environment
- [ ] Edit `/opt/arakis/.env`
- [ ] Set `OPENAI_API_KEY`
- [ ] Set `UNPAYWALL_EMAIL`
- [ ] Verify `SECRET_KEY` is set (auto-generated)
- [ ] Verify `POSTGRES_PASSWORD` is set (auto-generated)
- [ ] Verify `DATABASE_URL` is correct for Docker
- [ ] Set `DEBUG=false`
- [ ] Configure optional API keys (NCBI, Elsevier, etc.)
- [ ] Save and verify file permissions: `chmod 600 /opt/arakis/.env`

### 4. Start Services
- [ ] Start Arakis: `sudo systemctl start arakis`
- [ ] Check status: `sudo systemctl status arakis`
- [ ] Verify containers running: `docker ps`
- [ ] Check for errors: `sudo journalctl -u arakis -n 50`

### 5. Initialize Database
- [ ] Run migrations: `docker compose exec api alembic upgrade head`
- [ ] Verify tables created: `docker compose exec postgres psql -U arakis -d arakis -c "\dt"`
- [ ] Check migration status: `docker compose exec api alembic current`

### 6. SSL Configuration
- [ ] Verify SSL certificate obtained
- [ ] Check certificate: `sudo certbot certificates`
- [ ] Test auto-renewal: `sudo certbot renew --dry-run`
- [ ] Verify HTTPS redirect working

### 7. Health Checks
- [ ] Run health check script: `sudo /opt/arakis/deploy/health_check.sh --verbose`
- [ ] All critical checks should pass
- [ ] Test API health: `curl https://your-domain.com/health`
- [ ] Expected response: `{"status":"healthy","database":"connected"}`
- [ ] Access API docs: `https://your-domain.com/docs`

### 8. Functional Testing
- [ ] Test API root endpoint: `curl https://your-domain.com/`
- [ ] Create test workflow via API
- [ ] Verify workflow created in database
- [ ] Check workflow status endpoint
- [ ] Test authentication endpoints (if enabled)
- [ ] Review logs for errors: `docker logs arakis-api`

### 9. Security Hardening
- [ ] Verify firewall enabled: `sudo ufw status`
- [ ] Only ports 22, 80, 443 open
- [ ] Verify SSH key-only authentication (optional)
- [ ] Disable root SSH login (optional)
- [ ] Install fail2ban: `sudo apt install fail2ban`
- [ ] Enable auto security updates
- [ ] Review `.env` file permissions (should be 600)

### 10. Monitoring & Backups
- [ ] Verify backup cron job: `sudo crontab -l`
- [ ] Run manual backup test: `sudo /opt/arakis/deploy/backup.sh`
- [ ] Verify backup created in `/var/backups/arakis/`
- [ ] Test backup restore (on test database)
- [ ] Configure S3 backup upload (optional)
- [ ] Setup monitoring alerts (optional)

### 11. Performance Testing
- [ ] Test API response time: `time curl https://your-domain.com/health`
- [ ] Should be < 200ms
- [ ] Check resource usage: `docker stats --no-stream`
- [ ] API should use < 500MB RAM at idle
- [ ] PostgreSQL should use < 100MB RAM at idle
- [ ] Create test workflow and monitor resource usage

### 12. Documentation
- [ ] Document deployment date and configuration
- [ ] Save server IP, domain, and credentials securely
- [ ] Document any customizations made
- [ ] Share API documentation URL with team
- [ ] Create incident response plan

## Post-Deployment

### Immediate (First 24 Hours)
- [ ] Monitor logs continuously: `sudo journalctl -u arakis -f`
- [ ] Check health endpoint every hour
- [ ] Monitor resource usage: `docker stats`
- [ ] Verify SSL auto-renewal timer: `sudo systemctl status certbot.timer`
- [ ] Test backup at scheduled time
- [ ] Review nginx access logs for unusual traffic

### First Week
- [ ] Daily health checks
- [ ] Monitor disk space usage
- [ ] Review error logs
- [ ] Test application under normal load
- [ ] Verify backups running and accessible
- [ ] Check SSL certificate status

### Ongoing Maintenance
- [ ] Weekly: Review logs and metrics
- [ ] Monthly: Test backup restoration
- [ ] Monthly: Review and rotate logs
- [ ] Quarterly: Update dependencies
- [ ] Quarterly: Security audit
- [ ] As needed: Scale resources based on usage

## Troubleshooting Checklist

If deployment fails, check:

### Services Not Starting
- [ ] Check Docker daemon: `sudo systemctl status docker`
- [ ] Check disk space: `df -h`
- [ ] Check memory: `free -m`
- [ ] Review systemd logs: `sudo journalctl -u arakis -n 100`
- [ ] Check container logs: `docker logs arakis-api`

### Database Connection Issues
- [ ] Verify PostgreSQL container running: `docker ps | grep postgres`
- [ ] Test database connection: `docker compose exec postgres pg_isready`
- [ ] Check DATABASE_URL in .env
- [ ] Verify password matches in .env and docker-compose.yml

### SSL Certificate Issues
- [ ] Verify domain DNS: `dig your-domain.com`
- [ ] Check ports 80 and 443 open: `sudo ufw status`
- [ ] Check nginx logs: `sudo tail -f /var/log/nginx/error.log`
- [ ] Retry certificate: `sudo certbot --nginx -d your-domain.com`

### API Not Responding
- [ ] Check API container: `docker ps | grep api`
- [ ] Check API logs: `docker logs arakis-api`
- [ ] Verify health endpoint: `curl http://localhost:8000/health`
- [ ] Check nginx proxy: `sudo nginx -t`
- [ ] Verify ports not blocked: `sudo netstat -tlnp | grep 8000`

### Performance Issues
- [ ] Check resource usage: `docker stats`
- [ ] Check disk I/O: `iostat -x 1`
- [ ] Review slow queries in PostgreSQL logs
- [ ] Check Redis memory usage
- [ ] Review nginx access logs for traffic patterns

## Rollback Plan

If deployment fails and needs rollback:

### 1. Stop Services
```bash
sudo systemctl stop arakis
```

### 2. Restore Database
```bash
# Find latest backup
ls -lh /var/backups/arakis/

# Restore
gunzip -c /var/backups/arakis/arakis_backup_YYYYMMDD_HHMMSS.sql.gz | \
  docker compose exec -T postgres psql -U arakis -d arakis
```

### 3. Revert Code
```bash
cd /opt/arakis
git log --oneline -10  # Find previous commit
git checkout <previous-commit-hash>
```

### 4. Restart Services
```bash
sudo systemctl start arakis
```

### 5. Verify
```bash
curl https://your-domain.com/health
```

## Success Criteria

Deployment is successful when:

- [ ] All Docker containers running and healthy
- [ ] API health endpoint returns 200 OK
- [ ] HTTPS working with valid SSL certificate
- [ ] Database migrations completed
- [ ] Test workflow can be created via API
- [ ] Automated backups configured and tested
- [ ] No errors in logs
- [ ] Resource usage within acceptable limits
- [ ] Monitoring and alerts configured
- [ ] Documentation updated

## Sign-Off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Deployer | | | |
| Technical Lead | | | |
| Operations | | | |

## Notes

Use this section for deployment-specific notes, issues encountered, or customizations:

```
Date: __________
Notes:


```

---

**Version:** 1.0
**Last Updated:** January 2026
**Owner:** DevOps Team
