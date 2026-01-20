# Production Deployment Guide

This guide covers deploying the Sales Agent to production with safety, security, and observability.

## 📋 Pre-Deployment Checklist

### Security Validation

- [ ] **Secrets Management**
  ```bash
  make secrets-check --strict
  ```
  All critical secrets must be present before deployment.

- [ ] **OAuth Credentials**
  ```bash
  make auth-google --info
  ```
  Verify tokens are valid and scopes are correct.

- [ ] **Database Migration**
  ```bash
  alembic upgrade head
  ```
  Ensure all migrations are applied.

- [ ] **SSL/TLS Certificates**
  - [ ] Certificate is valid and not expired
  - [ ] Private key is secure (0600 permissions)
  - [ ] Certificate matches domain name

### Configuration Validation

- [ ] Environment is set to `production`
  ```bash
  echo $ENVIRONMENT  # Should output: production
  ```

- [ ] DRAFT_ONLY mode is enforced
  ```bash
  MODE_DRAFT_ONLY=true ALLOW_AUTO_SEND=false
  ```

- [ ] Approval workflow is enabled
  ```bash
  REQUIRE_APPROVAL=true
  ```

- [ ] Rate limiting is configured
  ```bash
  RATE_LIMIT_ENABLED=true RATE_LIMIT_REQUESTS=300
  ```

### Infrastructure

- [ ] PostgreSQL 15+ deployed and accessible
  - [ ] Backup strategy configured
  - [ ] Connection pooling enabled
  - [ ] SSL/TLS required for connections

- [ ] Redis 7+ deployed and accessible
  - [ ] Persistence enabled (AOF)
  - [ ] Password protected
  - [ ] Memory limits configured

- [ ] Celery workers ready
  - [ ] At least 2 worker instances
  - [ ] Auto-restart configured
  - [ ] Resource limits set

## 🚀 Deployment Steps

### 1. Build and Test

```bash
# Build Docker image with production tag
docker build -t sales-agent:1.0.0 -f Dockerfile.prod .

# Run integration tests against staging environment
docker run --env-file .env.staging \
  sales-agent:1.0.0 \
  pytest tests/integration -v

# Run smoke tests
docker run --env-file .env.staging \
  -e MODE=DRAFT_ONLY \
  sales-agent:1.0.0 \
  make smoke-formlead --mock
```

### 2. Database Preparation

```bash
# Create database backup (local first)
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d_%H%M%S).sql

# Apply migrations
alembic upgrade head

# Verify schema
psql $DATABASE_URL -c "\dt"
```

### 3. Deploy Application

```bash
# Using Docker Compose (recommended)
docker-compose -f docker-compose.prod.yml up -d

# Or using Kubernetes
kubectl apply -f k8s/prod/

# Verify services are running
docker ps -a
```

### 4. Verify Deployment

```bash
# Check application health
curl https://api.yourdomain.com/health

# Verify database connectivity
curl https://api.yourdomain.com/db/status

# Check worker status
celery inspect active -A src.celery_app

# View logs
docker logs -f $(docker ps -q -f ancestor=sales-agent:1.0.0)
```

### 5. Validate Integrations

```bash
# Google OAuth
curl -X POST https://api.yourdomain.com/auth/google/status

# HubSpot connectivity
curl -X GET https://api.yourdomain.com/connectors/hubspot/status

# Gmail API
curl -X GET https://api.yourdomain.com/connectors/gmail/status

# Calendar API
curl -X GET https://api.yourdomain.com/connectors/calendar/status
```

## 🔒 Security Hardening

### Network Security

```bash
# Enable HTTPS only
ENFORCE_HTTPS=true

# Set HSTS headers
HSTS_MAX_AGE=31536000
HSTS_INCLUDE_SUBDOMAINS=true

# Configure CORS
ALLOWED_ORIGINS=https://app.yourdomain.com,https://admin.yourdomain.com
```

### Database Security

```sql
-- Create dedicated app user
CREATE USER sales_agent_app WITH PASSWORD 'strong-password';

-- Grant minimal permissions
GRANT CONNECT ON DATABASE sales_agent TO sales_agent_app;
GRANT USAGE ON SCHEMA public TO sales_agent_app;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO sales_agent_app;

-- Disable default user
ALTER ROLE postgres PASSWORD 'random-very-strong-password';
```

### API Security

```python
# In production settings
RATE_LIMIT_ENABLED = True
RATE_LIMIT_REQUESTS = 300        # Per minute
RATE_LIMIT_PERIOD_SECONDS = 60

# API key rotation
API_KEY_ROTATION_DAYS = 90
```

### Audit & Monitoring

```python
# Enable comprehensive audit trail
AUDIT_TRAIL_ENABLED = True
AUDIT_TRAIL_RETENTION_DAYS = 90

# Enable security logging
LOG_LEVEL = "INFO"
LOG_FORMAT = "json"
SENTRY_ENABLED = True
```

## 📊 Monitoring & Observability

### Logs

```bash
# Stream application logs
docker logs -f app_container

# Search specific events
docker logs app_container | grep "ERROR"
docker logs app_container | grep "auth_success"

# Export logs for analysis
docker logs app_container 2>&1 | tee app_logs.txt
```

### Metrics

Monitor these key metrics:

- **API Response Time**: p50, p95, p99 latencies
- **Error Rate**: 5xx, 4xx errors per minute
- **Database Connections**: Active pools, queue depth
- **Email Workflow**:
  - Drafts created per hour
  - Approval response time
  - Failed sends (if enabled)
- **Celery Tasks**: Queue depth, worker utilization

### Health Checks

```bash
# Application health
GET /health
Response: {"status": "healthy", "version": "1.0.0"}

# Database health
GET /health/db
Response: {"status": "connected", "latency_ms": 5}

# Redis health
GET /health/redis
Response: {"status": "connected", "memory_mb": 128}

# Workers health
GET /health/workers
Response: {"status": "operational", "active_workers": 2}
```

### Alerting

Set up alerts for:

- [ ] API error rate > 1%
- [ ] Database connection failures
- [ ] Redis unavailable
- [ ] Worker queue depth > 1000
- [ ] Failed authentication attempts > 5 per minute
- [ ] Approval timeout without response
- [ ] Draft creation failures

## 🔄 Rollback Procedures

### Quick Rollback (Last Version)

```bash
# Scale down current version
docker-compose -f docker-compose.prod.yml down

# Revert to previous image
docker pull sales-agent:previous-version
docker-compose -f docker-compose.prod.yml up -d

# Verify
curl https://api.yourdomain.com/health
```

### Database Rollback

```bash
# Restore from backup
psql -d postgres -c "DROP DATABASE sales_agent;"
psql -d postgres -c "CREATE DATABASE sales_agent;"
psql $DATABASE_URL < backup_timestamp.sql

# Verify schema
alembic current
```

## 📝 Post-Deployment Checklist

- [ ] All health checks passing
- [ ] Audit trail logs flowing to Sentry
- [ ] Monitoring dashboards showing data
- [ ] Team notified of deployment
- [ ] Runbook documented
- [ ] On-call engineer knows rollback procedure
- [ ] Customer support notified of new features/changes

## 🚨 Troubleshooting

### OAuth Token Expired

```bash
# Refresh tokens
make auth-google --gmail --drive --calendar

# Verify new tokens work
make smoke-formlead --mock
```

### Database Connection Issues

```bash
# Check connection
psql $DATABASE_URL -c "SELECT NOW();"

# Verify pool
docker exec db_container \
  psql -U postgres -c "SELECT * FROM pg_stat_activity;"

# Restart connection pool
docker restart app_container
```

### High Memory Usage

```bash
# Check app memory
docker stats app_container

# Check Redis memory
redis-cli INFO memory

# Clear old audit logs
DELETE FROM audit_logs WHERE created_at < NOW() - INTERVAL '90 days';
```

## 🎯 Performance Optimization

### Database Indexing

```sql
-- Create indexes on frequently queried fields
CREATE INDEX idx_prospects_email ON prospects(email);
CREATE INDEX idx_drafts_status ON drafts(status) WHERE status != 'sent';
CREATE INDEX idx_tasks_contact_id ON tasks(contact_id);
CREATE INDEX idx_audit_logs_timestamp ON audit_logs(timestamp);
```

### Cache Strategy

```python
# Redis cache for contact data (1 hour TTL)
redis.setex(f"contact:{contact_id}", 3600, contact_json)

# Cache HubSpot company data (4 hours TTL)
redis.setex(f"company:{company_id}", 14400, company_json)
```

### Connection Pooling

```python
# PostgreSQL: Use connection pooling
SQLALCHEMY_ENGINE_OPTIONS = {
    "pool_size": 20,
    "pool_recycle": 3600,
    "pool_pre_ping": True,
}

# Redis: Use connection pool
redis_pool = redis.ConnectionPool(host="localhost", port=6379)
```

## 📞 Escalation Contacts

| Role | Contact | Phone |
|------|---------|-------|
| On-Call Engineer | [Assigned] | [Phone] |
| Database Admin | [Assigned] | [Phone] |
| Security Lead | [Assigned] | [Phone] |
| Product Manager | [Assigned] | [Phone] |

## 🔗 Related Documentation

- [DRAFT_ONLY Mode](./docs/DRAFT_ONLY_SETUP.md)
- [Manual Validation Checklist](./docs/MANUAL_VALIDATION_CHECKLIST.md)
- [Secrets Management](./docs/SECRETS_CHECK.md)
- [Google OAuth Setup](./docs/GOOGLE_OAUTH.md)
- [HubSpot Integration](./docs/HUBSPOT_WEBHOOK.md)
