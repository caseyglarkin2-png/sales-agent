# Disaster Recovery Runbook

**Last Updated:** 2026-01-23  
**Owner:** Engineering Team  
**Version:** 1.0

---

## Table of Contents

1. [Emergency Contacts](#emergency-contacts)
2. [Critical Systems](#critical-systems)
3. [RTO/RPO Targets](#rtorpo-targets)
4. [Backup Strategy](#backup-strategy)
5. [Recovery Procedures](#recovery-procedures)
6. [Incident Response](#incident-response)
7. [Testing Schedule](#testing-schedule)

---

## Emergency Contacts

| Role | Primary | Secondary | Phone |
|------|---------|-----------|-------|
| On-Call Engineer | TBD | TBD | TBD |
| Database Admin | TBD | TBD | TBD |
| Platform Lead | TBD | TBD | TBD |
| Security Lead | TBD | TBD | TBD |

**Escalation Path:**
1. On-Call Engineer (immediate)
2. Platform Lead (within 15 min)
3. CTO (within 30 min for P0)

---

## Critical Systems

### Tier 1 (Critical - RTO: 1 hour, RPO: 5 minutes)
- **PostgreSQL Database** - Primary data store
- **Redis Cache** - Session/rate limiting
- **API Server** - FastAPI application
- **Email Service** - Gmail/SendGrid connectors

### Tier 2 (Important - RTO: 4 hours, RPO: 1 hour)
- **Celery Workers** - Background tasks
- **RabbitMQ** - Task queue
- **OAuth Tokens** - Token storage

### Tier 3 (Standard - RTO: 24 hours, RPO: 24 hours)
- **Logs/Metrics** - Historical data
- **Analytics** - Reporting data

---

## RTO/RPO Targets

| System | RTO (Recovery Time) | RPO (Data Loss) | Backup Frequency |
|--------|---------------------|-----------------|------------------|
| PostgreSQL | 1 hour | 5 minutes | Every 5 min (WAL), Daily (full) |
| Redis | 1 hour | 15 minutes | Hourly snapshots |
| Application Code | 15 minutes | 0 (Git) | Continuous (Git) |
| Environment Config | 15 minutes | 0 (Git) | Continuous (Git) |
| OAuth Tokens | 4 hours | 1 hour | Hourly |

---

## Backup Strategy

### Database Backups

**PostgreSQL:**
- **Full Backup:** Daily at 2 AM UTC (pg_dump)
- **WAL Archiving:** Continuous (every 5 minutes)
- **Retention:** 30 days full, 7 days WAL
- **Location:** AWS S3 / GCS (encrypted)
- **Restoration Time:** ~30 minutes for 100GB

**Redis:**
- **RDB Snapshots:** Hourly
- **AOF Logs:** Continuous (if enabled)
- **Retention:** 7 days
- **Location:** Same cloud storage as PostgreSQL

**Backup Commands:**
```bash
# PostgreSQL full backup
/workspaces/sales-agent/infra/backup.sh --full

# PostgreSQL incremental (WAL)
/workspaces/sales-agent/infra/backup.sh --wal

# Redis snapshot
/workspaces/sales-agent/infra/backup.sh --redis
```

### Application Backups

**Code:**
- Stored in Git (GitHub)
- Tagged releases for each deployment
- Docker images pushed to registry

**Environment Variables:**
- Encrypted and stored in secrets manager
- Backup copy in 1Password/Vault

**Configuration:**
- Infrastructure as Code (IaC) in Git
- Docker Compose / Kubernetes manifests

---

## Recovery Procedures

### Complete System Failure

**Scenario:** Total datacenter failure, all services down

**Recovery Steps:**

1. **Activate Incident Response** (0-5 min)
   ```bash
   # Notify team via PagerDuty/Slack
   ./scripts/incident-declare.sh --severity P0
   ```

2. **Provision New Infrastructure** (5-20 min)
   ```bash
   # Deploy to backup region
   cd infra/
   terraform init
   terraform apply -var="region=us-west-2"
   ```

3. **Restore Database** (20-50 min)
   ```bash
   # Restore PostgreSQL from latest backup
   ./infra/restore.sh --db postgres --backup latest
   
   # Verify data integrity
   psql -c "SELECT COUNT(*) FROM prospects;"
   ```

4. **Deploy Application** (50-60 min)
   ```bash
   # Deploy latest stable release
   docker-compose -f docker-compose.prod.yml up -d
   
   # Verify health
   curl http://localhost:8000/health
   ```

5. **Validate Critical Paths** (60-70 min)
   ```bash
   # Test email sending
   curl -X POST http://localhost:8000/api/drafts/send-test
   
   # Test OAuth
   curl http://localhost:8000/api/auth/google/status
   ```

6. **Update DNS** (70-75 min)
   ```bash
   # Point DNS to new instance
   # Update A/CNAME records
   ```

7. **Monitor & Communicate** (75+ min)
   ```bash
   # Post status update
   ./scripts/status-update.sh --message "Services restored"
   
   # Monitor error rates
   watch -n 10 'curl http://localhost:8000/metrics'
   ```

### Database Corruption

**Scenario:** PostgreSQL data corruption detected

**Recovery Steps:**

1. **Stop Application** (Prevent further writes)
   ```bash
   docker-compose stop api celery
   ```

2. **Assess Corruption**
   ```bash
   psql -c "SELECT pg_database.datname, pg_database_size(pg_database.datname) FROM pg_database;"
   psql -c "VACUUM ANALYZE;"
   ```

3. **Restore from Backup**
   ```bash
   # Restore to point-in-time (5 min ago)
   ./infra/restore.sh --db postgres --pitr "5 minutes ago"
   ```

4. **Verify Restoration**
   ```bash
   psql -c "SELECT COUNT(*) FROM prospects;"
   psql -c "SELECT MAX(created_at) FROM prospects;"
   ```

5. **Restart Application**
   ```bash
   docker-compose up -d
   ```

### OAuth Token Loss

**Scenario:** OAuth tokens deleted or corrupted

**Recovery Steps:**

1. **Check Backup**
   ```bash
   ./infra/restore.sh --db oauth_tokens --list-backups
   ```

2. **Restore Tokens**
   ```bash
   ./infra/restore.sh --db oauth_tokens --backup latest
   ```

3. **Re-authenticate if Needed**
   ```bash
   # Users may need to re-auth
   # Send notification email
   ./scripts/send-reauth-email.sh
   ```

### Code Deployment Failure

**Scenario:** Bad deployment breaks production

**Recovery Steps:**

1. **Emergency Rollback**
   ```bash
   # Rollback to previous version
   ./scripts/rollback.sh --to-version v1.2.3
   ```

2. **Verify Rollback**
   ```bash
   curl http://localhost:8000/version
   ```

3. **Analyze Failure**
   ```bash
   # Check logs
   docker logs sales-agent-api --tail 100
   
   # Check Sentry
   open https://sentry.io/organizations/sales-agent/
   ```

---

## Incident Response

### Severity Levels

| Level | Description | Response Time | Escalation |
|-------|-------------|---------------|------------|
| **P0** | Complete outage | Immediate | CTO within 30 min |
| **P1** | Partial outage | Within 15 min | Platform Lead within 1 hour |
| **P2** | Degraded performance | Within 1 hour | Business hours |
| **P3** | Minor issues | Within 4 hours | Next business day |

### Incident Workflow

1. **Detect** - Monitoring alerts or user reports
2. **Declare** - Create incident ticket, notify team
3. **Triage** - Assess severity and impact
4. **Mitigate** - Implement temporary fix
5. **Resolve** - Permanent fix and validation
6. **Postmortem** - Document learnings (within 48 hours)

### Communication Templates

**P0 Incident - Initial:**
```
🚨 INCIDENT DECLARED
Severity: P0
Impact: Complete service outage
Started: 2026-01-23 14:00 UTC
Team: Investigating
ETA: TBD
Updates: Every 15 minutes
```

**P0 Incident - Update:**
```
⚠️ INCIDENT UPDATE
Root Cause: Database connection pool exhausted
Action: Restarting database connections
Progress: 60% complete
Next Update: 14:30 UTC
```

**P0 Incident - Resolved:**
```
✅ INCIDENT RESOLVED
Duration: 45 minutes
Root Cause: Database connection pool exhausted
Fix: Increased connection pool limit
Postmortem: Will publish within 48 hours
```

---

## Testing Schedule

### DR Test Calendar

| Test Type | Frequency | Last Run | Next Run |
|-----------|-----------|----------|----------|
| Database Restore | Monthly | TBD | TBD |
| Full Failover | Quarterly | TBD | TBD |
| Backup Verification | Weekly | TBD | TBD |
| Runbook Review | Monthly | TBD | TBD |

### Test Procedures

**Monthly Database Restore Test:**
1. Select random backup from last 30 days
2. Restore to isolated environment
3. Verify data integrity
4. Document restoration time
5. Update runbook if issues found

**Quarterly Failover Test:**
1. Schedule during low-traffic window
2. Fail over to backup region
3. Verify all services operational
4. Measure RTO achieved
5. Fail back to primary
6. Document lessons learned

---

## Backup Verification

### Automated Checks

```bash
# Daily backup verification script
/workspaces/sales-agent/infra/verify-backups.sh

# Checks:
# - Backup files exist in storage
# - Backup size within expected range
# - Latest backup timestamp within SLA
# - Backup integrity (checksum)
```

### Manual Verification (Monthly)

1. Download random backup
2. Restore to test database
3. Run data validation queries
4. Compare row counts with production
5. Test application against restored DB

---

## Rollback Procedures

### Emergency Rollback Script

**Location:** `/workspaces/sales-agent/scripts/rollback.sh`

**Usage:**
```bash
# Rollback to previous version
./scripts/rollback.sh

# Rollback to specific version
./scripts/rollback.sh --to-version v1.2.3

# Dry run (show what would happen)
./scripts/rollback.sh --dry-run
```

**What it does:**
1. Pull previous Docker image
2. Stop current containers
3. Start containers with previous image
4. Verify health checks pass
5. Send notification to team

---

## Monitoring & Alerts

### Critical Alerts

| Alert | Threshold | Action |
|-------|-----------|--------|
| API Error Rate | >5% in 5 min | Page on-call |
| Database CPU | >90% for 5 min | Page on-call |
| Disk Space | <10% free | Page on-call |
| Backup Failure | Any failure | Email team |
| OAuth Token Expiry | <1 hour | Refresh tokens |

### Monitoring Dashboards

- **Grafana:** http://grafana.example.com
- **Sentry:** http://sentry.io
- **Application Logs:** CloudWatch / Datadog

---

## Appendix

### Useful Commands

**Check service status:**
```bash
docker-compose ps
systemctl status sales-agent
```

**View logs:**
```bash
docker logs sales-agent-api -f
tail -f /var/log/sales-agent/api.log
```

**Database connections:**
```bash
psql -c "SELECT count(*) FROM pg_stat_activity;"
```

**Redis info:**
```bash
redis-cli INFO
redis-cli BGSAVE
```

### Checklist for New Engineers

- [ ] Review this runbook
- [ ] Access to backup storage (S3/GCS)
- [ ] SSH access to production servers
- [ ] PagerDuty/on-call rotation added
- [ ] Sentry access granted
- [ ] Grafana dashboards bookmarked
- [ ] Test restore procedure (supervised)
- [ ] Shadow on-call rotation (1 week)

---

**Document Maintenance:**
- Review quarterly
- Update after each incident
- Update after infrastructure changes
- Version control in Git
