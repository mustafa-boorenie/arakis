# Arakis CI/CD Guide

Complete guide for setting up and using the Continuous Integration and Continuous Deployment pipeline for Arakis.

## Overview

The Arakis CI/CD pipeline provides:
- ✅ Automated testing on every pull request
- ✅ Automated Docker image builds and security scans
- ✅ Automated deployment to production on merge to main
- ✅ Automatic rollback on failed health checks
- ✅ Zero-downtime deployments
- ✅ Comprehensive health checks and monitoring

## Architecture

```
Developer → GitHub → CI Workflow → Docker Build → CD Workflow → Production
                         ↓              ↓              ↓
                      Tests      Security Scan    Health Checks
                         ↓              ↓              ↓
                      [Pass]        [Pass]       [Pass/Rollback]
```

## Workflows

### 1. Continuous Integration (CI)

**File:** `.github/workflows/ci.yml`

**Triggers:**
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop`

**Jobs:**

#### Lint
- Runs `ruff` code linter
- Runs `ruff` formatter check
- Runs `mypy` type checker
- **Duration:** ~1-2 minutes

#### Test
- Sets up PostgreSQL and Redis test databases
- Installs system dependencies (tesseract, pandoc)
- Runs pytest with coverage
- Uploads coverage to Codecov
- **Duration:** ~5-10 minutes

#### Security
- Runs `bandit` security linter
- Checks dependencies with `safety`
- Uploads security reports
- **Duration:** ~2-3 minutes

#### Build Test
- Tests Docker image build
- Validates Dockerfile
- **Duration:** ~3-5 minutes

#### Integration Test
- Starts full Docker Compose stack
- Runs database migrations
- Tests API endpoints
- Verifies service health
- **Duration:** ~5-7 minutes

#### Report
- Aggregates all job results
- Reports overall status
- **Duration:** ~30 seconds

**Total Duration:** ~15-25 minutes

---

### 2. Docker Build and Push

**File:** `.github/workflows/docker-build.yml`

**Triggers:**
- Push to `main` branch
- Version tags (`v*.*.*`)
- Pull requests to `main`
- Manual workflow dispatch

**Jobs:**

#### Build
- Multi-architecture builds (amd64, arm64)
- Pushes to GitHub Container Registry
- Tags with branch, PR, version, and SHA
- Uses GitHub Actions cache for speed
- **Duration:** ~10-15 minutes

#### Scan
- Runs Trivy vulnerability scanner
- Runs Grype security scanner
- Uploads results to GitHub Security
- Generates SBOM (Software Bill of Materials)
- **Duration:** ~3-5 minutes

#### Test Image
- Pulls built image
- Tests container startup
- Verifies image runs correctly
- **Duration:** ~2-3 minutes

**Total Duration:** ~15-25 minutes

---

### 3. Continuous Deployment (CD)

**File:** `.github/workflows/cd.yml`

**Triggers:**
- Successful completion of CI and Docker Build workflows
- Manual workflow dispatch (with environment selection)

**Jobs:**

#### Check Tests
- Verifies CI workflow passed
- Blocks deployment if tests failed
- **Duration:** ~10 seconds

#### Backup
- Creates database backup before deployment
- Verifies backup was created
- **Duration:** ~1-2 minutes

#### Deploy
- SSH to production server
- Copies deployment script
- Runs automated deployment
- Updates code, Docker images, migrations
- **Duration:** ~3-5 minutes

#### Health Check
- Runs comprehensive health checks
- Verifies all services healthy
- Tests API endpoints
- Validates response content
- **Duration:** ~1-2 minutes

#### Smoke Test
- Tests critical API endpoints
- Verifies API documentation
- Checks SSL certificate
- **Duration:** ~30 seconds

#### Rollback (on failure)
- Automatically triggered if deployment fails
- Reverts to previous version
- Restores database from backup
- Verifies rollback successful
- **Duration:** ~3-5 minutes

#### Notify
- Reports deployment status
- Sends notifications (optional: Slack, Discord)
- **Duration:** ~10 seconds

**Total Duration:** ~8-15 minutes (successful), ~12-18 minutes (with rollback)

---

## Setup Instructions

### Prerequisites

1. **GitHub Repository**
   - Arakis code pushed to GitHub
   - Repository has GitHub Actions enabled

2. **Production Server**
   - Ubuntu 22.04 LTS server
   - Arakis deployed using Phase 4 setup
   - SSH access configured

3. **GitHub Container Registry**
   - Enabled for your repository
   - Permissions set correctly

### Step 1: Configure GitHub Secrets

Navigate to: **Settings → Secrets and variables → Actions**

Add the following secrets:

#### Required Secrets

| Secret Name | Description | Example |
|------------|-------------|---------|
| `DEPLOY_SSH_KEY` | Private SSH key for deployment | (RSA private key) |
| `DEPLOY_HOST` | Production server hostname/IP | `123.45.67.89` |
| `DEPLOY_DOMAIN` | Production domain | `arakis.example.com` |

#### Optional Secrets (for notifications)

| Secret Name | Description |
|------------|-------------|
| `SLACK_WEBHOOK_URL` | Slack webhook for notifications |
| `DISCORD_WEBHOOK_URL` | Discord webhook for notifications |

### Step 2: Generate SSH Key for Deployment

On your local machine:

```bash
# Generate SSH key pair
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/.ssh/arakis_deploy_key

# Copy public key to server
ssh-copy-id -i ~/.ssh/arakis_deploy_key.pub deploy-user@your-server.com

# Copy private key content
cat ~/.ssh/arakis_deploy_key
# Copy the entire output and save as DEPLOY_SSH_KEY secret
```

### Step 3: Create Deploy User on Server

SSH to your production server:

```bash
# Create deploy user
sudo useradd -m -s /bin/bash arakis-deploy

# Add to docker group
sudo usermod -aG docker arakis-deploy

# Give sudo permissions for deployment scripts
echo "arakis-deploy ALL=(ALL) NOPASSWD: /opt/arakis/scripts/deploy.sh, /opt/arakis/scripts/rollback.sh, /opt/arakis/deploy/backup.sh, /opt/arakis/deploy/health_check.sh, /usr/bin/docker" | sudo tee /etc/sudoers.d/arakis-deploy

# Set up SSH for deploy user
sudo mkdir -p /home/arakis-deploy/.ssh
sudo cp ~/.ssh/authorized_keys /home/arakis-deploy/.ssh/
sudo chown -R arakis-deploy:arakis-deploy /home/arakis-deploy/.ssh
sudo chmod 700 /home/arakis-deploy/.ssh
sudo chmod 600 /home/arakis-deploy/.ssh/authorized_keys
```

### Step 4: Update Workflow Files

Edit `.github/workflows/docker-build.yml` and `.github/workflows/cd.yml`:

Replace `yourusername/arakis` with your GitHub username/organization and repository name.

```yaml
# In docker-build.yml
env:
  REGISTRY: ghcr.io
  IMAGE_NAME: yourusername/arakis  # Update this
```

```bash
# In scripts/deploy.sh
IMAGE_REPO="yourusername/arakis"  # Update this
```

### Step 5: Test CI Workflow

Create a test branch and pull request:

```bash
git checkout -b test-ci
git commit --allow-empty -m "Test CI workflow"
git push origin test-ci
```

Create a pull request and verify:
- All CI jobs pass (lint, test, security, build-test, integration-test)
- Check Actions tab for workflow runs

### Step 6: Test Docker Build

Merge the PR or push to main:

```bash
git checkout main
git merge test-ci
git push origin main
```

Verify:
- Docker Build workflow runs
- Image pushed to GitHub Container Registry
- Security scans complete
- Check: `https://github.com/yourusername/arakis/pkgs/container/arakis`

### Step 7: Test CD Workflow (Manual)

Trigger manual deployment:

1. Go to **Actions** tab
2. Select **Continuous Deployment** workflow
3. Click **Run workflow**
4. Select environment: `production`
5. Click **Run workflow**

Verify:
- Backup job creates backup
- Deploy job completes successfully
- Health checks pass
- Smoke tests pass
- API accessible at your domain

### Step 8: Verify Automatic Deployment

Make a small change and push to main:

```bash
# Update README or add a comment
git commit -m "Test automatic deployment"
git push origin main
```

Verify:
- CI workflow runs and passes
- Docker Build workflow runs and pushes image
- CD workflow triggers automatically
- Deployment completes successfully

---

## Usage

### Normal Development Flow

1. **Create feature branch**
   ```bash
   git checkout -b feature/my-feature
   ```

2. **Make changes and commit**
   ```bash
   git add .
   git commit -m "Add my feature"
   git push origin feature/my-feature
   ```

3. **Create pull request**
   - Go to GitHub and create PR
   - CI workflow runs automatically
   - Wait for tests to pass
   - Get code review

4. **Merge to main**
   - Merge PR when approved
   - CI and Docker Build run automatically
   - CD workflow deploys to production
   - Deployment verified with health checks

5. **Monitor deployment**
   - Check Actions tab for status
   - Verify API at https://your-domain.com/health
   - Check logs if needed

### Emergency Hotfix

1. **Create hotfix branch from main**
   ```bash
   git checkout main
   git pull
   git checkout -b hotfix/critical-bug
   ```

2. **Fix bug and test locally**
   ```bash
   # Make fix
   pytest tests/
   docker compose up
   ```

3. **Push and merge quickly**
   ```bash
   git commit -m "Fix critical bug"
   git push origin hotfix/critical-bug
   # Create PR, get quick review, merge
   ```

4. **Monitor deployment**
   - CD workflow deploys automatically
   - Watch health checks
   - Verify fix in production

### Manual Deployment

If you need to deploy manually:

1. **SSH to server**
   ```bash
   ssh arakis-deploy@your-server.com
   ```

2. **Run deployment script**
   ```bash
   cd /opt/arakis
   sudo ./scripts/deploy.sh
   ```

3. **Verify health**
   ```bash
   sudo ./deploy/health_check.sh --verbose
   ```

### Manual Rollback

If automatic rollback fails or you need to rollback later:

1. **SSH to server**
   ```bash
   ssh arakis-deploy@your-server.com
   ```

2. **Run rollback script**
   ```bash
   cd /opt/arakis
   sudo ./scripts/rollback.sh
   ```

3. **Verify health**
   ```bash
   curl http://localhost:8000/health
   sudo ./deploy/health_check.sh --verbose
   ```

---

## Monitoring

### GitHub Actions

Monitor workflows:
- **Actions tab**: `https://github.com/yourusername/arakis/actions`
- Filter by workflow, branch, or status
- View logs for each job
- Download artifacts (coverage reports, security scans)

### Deployment Status

Check deployment status:
- Look for green checkmark in commit
- Check Actions tab for workflow status
- View deployment logs in workflow run

### Production Health

Monitor production:
- **API Health**: `https://your-domain.com/health`
- **API Docs**: `https://your-domain.com/docs`
- **Server Health**: SSH and run `./deploy/health_check.sh --json`

### Logs

View logs:
- **GitHub Actions**: In workflow run details
- **Server Logs**:
  ```bash
  sudo journalctl -u arakis -f
  docker logs -f arakis-api
  tail -f /var/log/arakis-deploy.log
  tail -f /var/log/arakis-rollback.log
  ```

---

## Troubleshooting

### CI Workflow Fails

#### Tests Fail

```bash
# Run tests locally
pytest tests/ -v

# Check specific test
pytest tests/test_specific.py::test_function -v

# Run with coverage
pytest tests/ --cov=arakis
```

#### Linting Fails

```bash
# Run linter locally
ruff check src/

# Auto-fix issues
ruff check src/ --fix

# Check formatting
ruff format --check src/

# Auto-format
ruff format src/
```

#### Security Scan Fails

```bash
# Run bandit locally
bandit -r src/ -ll

# Check dependencies
safety check
```

### Docker Build Fails

#### Build Errors

```bash
# Build locally
docker build -t arakis:test .

# Check build logs
docker build -t arakis:test . --progress=plain
```

#### Push Fails

- Verify GitHub token permissions
- Check Container Registry settings
- Ensure workflow has `packages: write` permission

### CD Workflow Fails

#### SSH Connection Fails

- Verify `DEPLOY_SSH_KEY` is correct
- Check `DEPLOY_HOST` is accessible
- Test SSH manually: `ssh arakis-deploy@your-server.com`
- Check server firewall allows SSH

#### Deployment Script Fails

```bash
# SSH to server
ssh arakis-deploy@your-server.com

# Check logs
sudo tail -f /var/log/arakis-deploy.log

# Check Docker
docker ps -a
docker logs arakis-api

# Check disk space
df -h
```

#### Health Checks Fail

```bash
# Run health check
sudo /opt/arakis/deploy/health_check.sh --verbose

# Check specific service
docker compose ps
docker logs arakis-postgres
docker logs arakis-redis

# Check API
curl http://localhost:8000/health
```

### Rollback Fails

#### No Backup Found

```bash
# List backups
ls -lh /var/backups/arakis/

# Create backup
sudo /opt/arakis/deploy/backup.sh

# Rollback without DB
sudo /opt/arakis/scripts/rollback.sh --skip-db
```

#### Database Restore Fails

```bash
# Check backup integrity
gunzip -t /var/backups/arakis/latest_backup.sql.gz

# Manual restore
gunzip -c /var/backups/arakis/backup.sql.gz | \
  docker compose exec -T postgres psql -U arakis -d arakis
```

---

## Best Practices

### Development

1. **Always create feature branches** - Never commit directly to main
2. **Write tests** - Add tests for new features
3. **Run tests locally** - Before pushing, run `pytest tests/`
4. **Keep PRs small** - Easier to review and deploy
5. **Use conventional commits** - Clear commit messages

### Deployment

1. **Deploy during low traffic** - Minimize user impact
2. **Monitor after deployment** - Watch for errors for 15-30 minutes
3. **One change at a time** - Easier to identify issues
4. **Have rollback plan** - Always know how to rollback
5. **Communicate** - Notify team about deployments

### Security

1. **Rotate secrets** - Update SSH keys and tokens periodically
2. **Limit permissions** - Deploy user has minimal required permissions
3. **Review security scans** - Check Trivy and Grype results
4. **Update dependencies** - Keep dependencies up to date
5. **Monitor logs** - Watch for suspicious activity

---

## Advanced Topics

### Blue-Green Deployment

For zero-downtime deployments with instant rollback:

1. Run two identical production environments (blue and green)
2. Deploy to inactive environment
3. Run health checks
4. Switch traffic to new environment
5. Keep old environment for instant rollback

### Canary Deployment

For gradual rollouts:

1. Deploy to small subset of servers
2. Route 10% of traffic to new version
3. Monitor metrics and errors
4. Gradually increase traffic (25%, 50%, 100%)
5. Rollback if issues detected

### Multi-Environment

Set up staging environment:

1. Create `staging` branch
2. Deploy to staging server on push to `staging`
3. Test thoroughly in staging
4. Merge `staging` to `main` for production deployment

### Notifications

Add Slack notifications:

```yaml
- name: Send Slack notification
  uses: slackapi/slack-github-action@v1
  with:
    webhook-url: ${{ secrets.SLACK_WEBHOOK_URL }}
    payload: |
      {
        "text": "Deployment ${{ job.status }}",
        "blocks": [
          {
            "type": "section",
            "text": {
              "type": "mrkdwn",
              "text": "*Arakis Deployment*\nStatus: ${{ job.status }}\nCommit: ${{ github.sha }}"
            }
          }
        ]
      }
```

---

## Metrics and KPIs

Track these metrics:

- **Deployment Frequency** - How often you deploy
- **Lead Time** - Time from commit to production
- **Mean Time to Recovery (MTTR)** - Time to recover from failures
- **Change Failure Rate** - Percentage of deployments that fail
- **Deployment Duration** - Time taken to deploy

**Target Goals:**
- Deployment frequency: Daily or multiple times per day
- Lead time: < 1 hour
- MTTR: < 15 minutes
- Change failure rate: < 15%
- Deployment duration: < 10 minutes

---

## Support

- **Documentation**: This guide and `scripts/README.md`
- **GitHub Discussions**: Ask questions in repository discussions
- **GitHub Issues**: Report bugs or request features
- **Workflow Logs**: Check Actions tab for detailed logs

---

## Quick Reference

### Commands

```bash
# Local testing
pytest tests/
docker compose up
ruff check src/

# Manual deployment
ssh arakis-deploy@your-server.com
sudo /opt/arakis/scripts/deploy.sh

# Manual rollback
sudo /opt/arakis/scripts/rollback.sh

# Health check
sudo /opt/arakis/deploy/health_check.sh --verbose

# View logs
sudo journalctl -u arakis -f
docker logs -f arakis-api
```

### GitHub Secrets

- `DEPLOY_SSH_KEY` - SSH private key
- `DEPLOY_HOST` - Server IP/hostname
- `DEPLOY_DOMAIN` - Production domain

### Workflow Files

- `.github/workflows/ci.yml` - Continuous Integration
- `.github/workflows/docker-build.yml` - Docker builds
- `.github/workflows/cd.yml` - Continuous Deployment
- `scripts/deploy.sh` - Deployment automation
- `scripts/rollback.sh` - Rollback automation
