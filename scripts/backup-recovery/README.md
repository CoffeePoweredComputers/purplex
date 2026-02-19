# Purplex PostgreSQL Backup & Recovery

This directory contains automated backup and disaster recovery scripts for Purplex's PostgreSQL database.

## 📋 Overview

- **Automated daily backups** to local storage and AWS S3
- **30-day retention** with automatic cleanup
- **Point-in-time recovery** from any backup
- **Tested restore procedures** for disaster recovery
- **Low overhead** - backups complete in 2-5 minutes for typical databases

## 🗂️ Files

### Core Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| `backup-postgres.sh` | Main backup script | `./backup-postgres.sh` |
| `restore-from-local.sh` | Restore from local backup | `./restore-from-local.sh [backup-file]` |
| `restore-from-s3.sh` | Restore from S3 backup | `./restore-from-s3.sh [s3-key]` |
| `list-backups.sh` | List available backups | `./list-backups.sh` |

### Configuration Files

| File | Purpose |
|------|---------|
| `s3-lifecycle-policy.json` | S3 lifecycle policy (30-day retention) |
| `backup-iam-policy.json` | IAM policy for S3 backup access |
| `../systemd/purplex-backup.service` | Systemd service definition |
| `../systemd/purplex-backup.timer` | Systemd timer (daily at 2 AM) |

## 🚀 Quick Start

### 1. Prerequisites

```bash
# Required tools
- Docker (for database access)
- gzip (for compression)
- AWS CLI (for S3 uploads - optional)

# Required setup
- PostgreSQL container running (purplex_postgres)
- Directories: /home/ubuntu/backups, /home/ubuntu/logs
- AWS IAM role attached to EC2 instance (for S3)
```

### 2. Test Backup (Manual)

```bash
# Run backup manually
cd /home/anavarre/Projects/purplex/scripts/backup-recovery
./backup-postgres.sh

# Verify backup created
ls -lh /home/ubuntu/backups/postgres/

# List all backups
./list-backups.sh
```

### 3. Set Up Automated Backups

#### Option A: Systemd Timer (Recommended)

```bash
# Copy systemd files
sudo cp ../systemd/purplex-backup.service /etc/systemd/system/
sudo cp ../systemd/purplex-backup.timer /etc/systemd/system/

# Update paths in service file if needed
sudo nano /etc/systemd/system/purplex-backup.service

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable purplex-backup.timer
sudo systemctl start purplex-backup.timer

# Verify
sudo systemctl status purplex-backup.timer
sudo systemctl list-timers --all | grep purplex
```

#### Option B: Cron Job (Alternative)

```bash
# Edit crontab
crontab -e

# Add line (runs daily at 2 AM UTC)
0 2 * * * /home/anavarre/Projects/purplex/scripts/backup-recovery/backup-postgres.sh
```

### 4. Configure AWS S3 (Optional but Recommended)

```bash
# 1. Create S3 bucket
BUCKET_NAME="purplex-db-backups"
AWS_REGION="us-east-1"  # Change to your region

aws s3 mb s3://${BUCKET_NAME} --region ${AWS_REGION}

# 2. Enable versioning
aws s3api put-bucket-versioning \
    --bucket ${BUCKET_NAME} \
    --versioning-configuration Status=Enabled

# 3. Enable encryption
aws s3api put-bucket-encryption \
    --bucket ${BUCKET_NAME} \
    --server-side-encryption-configuration '{
        "Rules": [{
            "ApplyServerSideEncryptionByDefault": {
                "SSEAlgorithm": "AES256"
            },
            "BucketKeyEnabled": true
        }]
    }'

# 4. Block public access
aws s3api put-public-access-block \
    --bucket ${BUCKET_NAME} \
    --public-access-block-configuration \
        "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

# 5. Apply lifecycle policy
aws s3api put-bucket-lifecycle-configuration \
    --bucket ${BUCKET_NAME} \
    --lifecycle-configuration file://s3-lifecycle-policy.json

# 6. Create IAM policy and attach to EC2 role
aws iam create-policy \
    --policy-name PurplexBackupPolicy \
    --policy-document file://backup-iam-policy.json

aws iam attach-role-policy \
    --role-name purplex-ec2-role \
    --policy-arn arn:aws:iam::YOUR_ACCOUNT_ID:policy/PurplexBackupPolicy
```

## 🔄 Restore Procedures

### Restore from Local Backup

```bash
# Interactive restore (shows list of backups)
./restore-from-local.sh

# Restore specific backup
./restore-from-local.sh /home/ubuntu/backups/postgres/2025-09-29/purplex_purplex_prod_2025-09-29_02-00-00.sql.gz
```

### Restore from S3 Backup

```bash
# Interactive restore (shows list of S3 backups)
./restore-from-s3.sh

# Restore specific S3 backup
./restore-from-s3.sh daily/2025-09-29/purplex_purplex_prod_2025-09-29_02-00-00.sql.gz
```

### ⚠️ IMPORTANT: Restore Process

1. **STOPS** all application services (web, celery)
2. **TERMINATES** all database connections
3. **DROPS** the existing database
4. **RESTORES** from backup
5. **RUNS** Django migrations
6. **RESTARTS** services

**This process will cause downtime and data loss for recent changes!**

## 🔍 Monitoring

### Check Backup Status

```bash
# View backup logs
tail -f /home/ubuntu/logs/backup-postgres.log

# Check systemd service logs
sudo journalctl -u purplex-backup.service -n 50

# Check next scheduled backup
sudo systemctl list-timers purplex-backup.timer
```

### List Available Backups

```bash
# List all backups (local and S3)
./list-backups.sh

# List only local backups
find /home/ubuntu/backups/postgres -name "*.sql.gz" -type f -ls

# List only S3 backups
aws s3 ls s3://purplex-db-backups/daily/ --recursive --human-readable
```

## 📊 Recovery Objectives

### Recovery Point Objective (RPO): 24 hours
- Daily backups at 2 AM UTC
- Maximum data loss: 24 hours of activity

### Recovery Time Objective (RTO): 2 hours
- Includes detection, provisioning, restore, and verification

### Database Size Estimates

| Database Size | Backup Time | Restore Time | S3 Transfer |
|---------------|-------------|--------------|-------------|
| < 1 GB        | 2-5 min     | 5-10 min     | 1-2 min     |
| 1-10 GB       | 5-15 min    | 15-30 min    | 5-10 min    |
| 10-50 GB      | 15-45 min   | 30-90 min    | 15-30 min   |

## 🔧 Configuration

### Environment Variables

All scripts support these environment variables:

```bash
# Database Configuration
DB_CONTAINER=purplex_postgres    # PostgreSQL container name
DB_NAME=purplex_prod            # Database name
DB_USER=purplex_user            # Database user

# Backup Configuration
BACKUP_DIR=/home/ubuntu/backups/postgres    # Local backup directory
LOG_DIR=/home/ubuntu/logs                   # Log directory

# S3 Configuration
S3_BUCKET=purplex-db-backups    # S3 bucket name
S3_PREFIX=daily                 # S3 prefix for backups

# Retention
LOCAL_RETENTION_DAYS=7          # Keep local backups for 7 days
S3_RETENTION_DAYS=30            # Keep S3 backups for 30 days (lifecycle policy)
```

### Development/Testing Configuration

```bash
# For development (no AWS needed)
export BACKUP_DIR="/tmp/purplex-backups"
export LOG_DIR="/tmp/logs"
export DB_NAME="purplex_dev"

# Run backup
./backup-postgres.sh

# S3 upload will be skipped if AWS CLI not configured
```

## 🧪 Testing

### Test Backup Creation

```bash
# Run backup manually
./backup-postgres.sh

# Verify backup file created
LATEST_BACKUP=$(find /home/ubuntu/backups/postgres -name "*.sql.gz" -type f -print -quit)
echo "Latest backup: $LATEST_BACKUP"

# Check backup file integrity
gzip -t "$LATEST_BACKUP" && echo "✓ Backup file is valid"
```

### Test Restore (Non-Production)

```bash
# Create test database
docker exec purplex_postgres psql -U purplex_user -d postgres -c "CREATE DATABASE test_restore;"

# Restore to test database
LATEST_BACKUP=$(find /home/ubuntu/backups/postgres -name "*.sql.gz" -type f -print -quit)
gunzip -c "$LATEST_BACKUP" | docker exec -i purplex_postgres \
    pg_restore -U purplex_user -d test_restore --no-owner --no-acl

# Verify data
docker exec purplex_postgres psql -U purplex_user -d test_restore -c "
    SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
    FROM pg_tables
    WHERE schemaname = 'public'
    ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
    LIMIT 10;
"

# Cleanup test database
docker exec purplex_postgres psql -U purplex_user -d postgres -c "DROP DATABASE test_restore;"
```

## 💰 Cost Estimation

### S3 Storage (us-east-1)

Assumptions:
- Database size: 2 GB compressed
- Daily backups: 30 days retention

**Monthly Costs:**
- Standard storage (7 days): ~$0.32
- Glacier IR (23 days): ~$0.18
- PUT requests: ~$0.0002
- **Total: ~$0.50/month**

For larger databases:
- 5 GB: ~$1.25/month
- 10 GB: ~$2.50/month
- 50 GB: ~$12.50/month

## 🔒 Security

- ✅ **S3 encryption at rest** (AES-256)
- ✅ **TLS encryption in transit** (AWS CLI default)
- ✅ **IAM role-based access** (no long-term credentials)
- ✅ **S3 public access blocked**
- ✅ **S3 versioning enabled**
- ⚠️ **Local backups unencrypted** (use encrypted EBS volumes)

## 🐛 Troubleshooting

### Backup Fails: "Container not running"

```bash
# Check container status
docker ps | grep postgres

# Restart container
docker-compose restart postgres
```

### Backup Fails: "S3 upload error"

```bash
# Check AWS credentials
aws sts get-caller-identity

# Check bucket exists
aws s3 ls s3://purplex-db-backups/

# Check IAM permissions
aws iam get-role-policy --role-name purplex-ec2-role --policy-name PurplexBackupPolicy
```

### Disk Space Issues

```bash
# Check disk usage
df -h

# Find large backup files
du -sh /home/ubuntu/backups/*

# Manually clean old backups
find /home/ubuntu/backups -name "*.sql.gz" -mtime +7 -delete
```

## 📅 Maintenance Schedule

### Weekly
- Check backup logs for errors
- Verify S3 uploads are occurring
- Monitor disk space usage

### Monthly
- Test restore procedure (dry run)
- Review backup sizes and trends
- Verify IAM permissions

### Quarterly
- Full disaster recovery drill
- Review and update documentation
- Audit backup retention policy

## 🆘 Emergency Restore

In case of catastrophic failure:

1. **Assess situation** - What failed? (instance, volume, database)
2. **Provision new resources** if needed (EC2 instance, volumes)
3. **Install Docker and dependencies**
4. **Download this repository**
5. **Run restore script**:
   ```bash
   ./restore-from-s3.sh  # Interactive - shows available backups
   ```
6. **Verify data integrity**
7. **Update DNS** if IP changed
8. **Resume operations**

## 📚 Additional Resources

- [AWS S3 Best Practices](https://docs.aws.amazon.com/AmazonS3/latest/userguide/security-best-practices.html)
- [PostgreSQL Backup Documentation](https://www.postgresql.org/docs/current/backup.html)
- [Django Migrations Guide](https://docs.djangoproject.com/en/stable/topics/migrations/)

## 📝 Notes

- **All restore operations require manual confirmation** to prevent accidental data loss
- **Backups are compressed** with gzip for space efficiency
- **Local backups are kept for 7 days**, S3 backups for 30 days
- **pg_dump custom format** allows parallel restore for large databases
- **--no-owner and --no-acl** flags prevent permission issues during restore