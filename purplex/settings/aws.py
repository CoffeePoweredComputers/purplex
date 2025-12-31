"""
AWS-specific production settings for Purplex.
These settings extend production.py for AWS deployment.
"""

import os

from .production import *  # noqa: F401, F403

# AWS Configuration
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

# Trust proxy headers from Nginx/ALB
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Allow health checks from AWS ALB/ELB
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "").split(",")
# Add EC2 instance metadata service for health checks
ALLOWED_HOSTS.extend(["169.254.169.254", "localhost", "127.0.0.1"])

# Remove strict host checking for initial deployment (update after domain setup)
if os.environ.get("INITIAL_DEPLOYMENT", "false").lower() == "true":
    ALLOWED_HOSTS = ["*"]
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
    print("WARNING: Running in initial deployment mode - security reduced!")

# CORS configuration for AWS
CORS_ALLOWED_ORIGINS = os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",")
if os.environ.get("CORS_ALLOW_ALL", "false").lower() == "true":
    CORS_ALLOW_ALL_ORIGINS = True  # Only for initial testing

# S3 Configuration (if using S3 for static/media)
USE_S3 = os.environ.get("USE_S3", "false").lower() == "true"

if USE_S3:
    # AWS credentials
    AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
    AWS_S3_REGION_NAME = os.environ.get("AWS_S3_REGION_NAME", "us-east-1")

    # S3 bucket configuration
    AWS_STORAGE_BUCKET_NAME = os.environ.get("AWS_STORAGE_BUCKET_NAME")
    AWS_S3_CUSTOM_DOMAIN = os.environ.get("AWS_S3_CUSTOM_DOMAIN")
    if AWS_S3_CUSTOM_DOMAIN:
        AWS_S3_CUSTOM_DOMAIN = f"{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com"

    # S3 static files configuration
    AWS_LOCATION = "static"
    STATIC_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/{AWS_LOCATION}/"
    STATICFILES_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"

    # S3 media files configuration
    DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
    MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/media/"

    # S3 optimization
    AWS_S3_FILE_OVERWRITE = False
    AWS_DEFAULT_ACL = "public-read"
    AWS_S3_OBJECT_PARAMETERS = {
        "CacheControl": "max-age=86400",  # 1 day
    }

    # Remove WhiteNoise when using S3
    if "whitenoise.middleware.WhiteNoiseMiddleware" in MIDDLEWARE:  # noqa: F405
        MIDDLEWARE.remove("whitenoise.middleware.WhiteNoiseMiddleware")  # noqa: F405

# CloudWatch Logging (optional)
if os.environ.get("USE_CLOUDWATCH", "false").lower() == "true":
    LOGGING["handlers"]["cloudwatch"] = {  # noqa: F405
        "class": "watchtower.CloudWatchLogHandler",
        "log_group": "purplex",
        "stream_name": "django",
        "level": "INFO",
    }
    LOGGING["root"]["handlers"].append("cloudwatch")  # noqa: F405
    LOGGING["loggers"]["django"]["handlers"].append("cloudwatch")  # noqa: F405
    LOGGING["loggers"]["purplex"]["handlers"].append("cloudwatch")  # noqa: F405

# ElastiCache Redis configuration (if using)
if os.environ.get("USE_ELASTICACHE", "false").lower() == "true":
    REDIS_HOST = os.environ.get("ELASTICACHE_ENDPOINT", "redis")
    CACHES["default"]["LOCATION"] = f"redis://{REDIS_HOST}:6379/1"  # noqa: F405
    CELERY_BROKER_URL = f"redis://{REDIS_HOST}:6379/0"
    CELERY_RESULT_BACKEND = f"redis://{REDIS_HOST}:6379/0"

# RDS Database configuration (if using)
if os.environ.get("USE_RDS", "false").lower() == "true":
    DATABASES["default"] = {  # noqa: F405
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("RDS_DB_NAME"),
        "USER": os.environ.get("RDS_USERNAME"),
        "PASSWORD": os.environ.get("RDS_PASSWORD"),
        "HOST": os.environ.get("RDS_HOSTNAME"),
        "PORT": os.environ.get("RDS_PORT", "5432"),
        "CONN_MAX_AGE": 600,
        "OPTIONS": {"connect_timeout": 10, "options": "-c statement_timeout=30000"},
    }

# AWS Secrets Manager (if using)
if os.environ.get("USE_SECRETS_MANAGER", "false").lower() == "true":
    import json

    import boto3

    def get_secret(secret_name):
        session = boto3.session.Session()
        client = session.client(service_name="secretsmanager", region_name=AWS_REGION)

        try:
            get_secret_value_response = client.get_secret_value(SecretId=secret_name)
            secret = get_secret_value_response["SecretString"]
            return json.loads(secret)
        except Exception as e:
            print(f"Error retrieving secret {secret_name}: {e}")
            return {}

    # Load secrets
    secrets = get_secret("purplex/production")
    if secrets:
        SECRET_KEY = secrets.get("django_secret_key", SECRET_KEY)  # noqa: F405
        DATABASES["default"]["PASSWORD"] = secrets.get(  # noqa: F405
            "db_password",
            DATABASES["default"]["PASSWORD"],  # noqa: F405
        )
        OPENAI_API_KEY = secrets.get("openai_api_key", OPENAI_API_KEY)  # noqa: F405

# Email configuration for AWS SES
if os.environ.get("USE_SES", "false").lower() == "true":
    EMAIL_BACKEND = "django_ses.SESBackend"
    AWS_SES_REGION_NAME = os.environ.get("AWS_SES_REGION_NAME", "us-east-1")
    AWS_SES_REGION_ENDPOINT = f"email.{AWS_SES_REGION_NAME}.amazonaws.com"

# Performance optimizations for AWS
if os.environ.get("USE_ELASTICACHE", "false").lower() == "true":
    # Use ElastiCache for session storage
    SESSION_ENGINE = "django.contrib.sessions.backends.cache"
    SESSION_CACHE_ALIAS = "default"

# Monitoring
if os.environ.get("USE_XRAY", "false").lower() == "true":
    # AWS X-Ray for distributed tracing
    INSTALLED_APPS.append("aws_xray_sdk.ext.django")  # noqa: F405
    MIDDLEWARE.insert(0, "aws_xray_sdk.ext.django.middleware.XRayMiddleware")  # noqa: F405
    XRAY_RECORDER = {
        "AWS_XRAY_TRACING_NAME": "purplex",
        "AWS_XRAY_CONTEXT_MISSING": "LOG_ERROR",
    }

# Health check URL for ALB/ELB
HEALTH_CHECK_URL = "/api/health/"

print(f"AWS settings loaded for region: {AWS_REGION}")
if USE_S3:
    print(f"Using S3 for static/media: {AWS_STORAGE_BUCKET_NAME}")
if os.environ.get("USE_RDS", "false").lower() == "true":
    print(f"Using RDS database: {os.environ.get('RDS_HOSTNAME')}")
