# LTI 1.3 Canvas Integration - Complete Implementation Guide

> **Status: Design Document / Implementation Plan**
>
> This document describes a **planned feature** that has not yet been implemented. The LTI app (`purplex/lti/`) does not currently exist in the codebase. Use this guide when implementing LTI support.

This document provides a comprehensive implementation guide for adding LTI 1.3 (Learning Tools Interoperability) support to Purplex, enabling secure iframe embedding in Canvas LMS with verified authentication and automatic grade passback.

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Dependencies](#dependencies)
4. [Pre-Implementation Checklist](#pre-implementation-checklist)
5. [Backend Implementation](#backend-implementation)
   - [Django App Structure](#django-app-structure)
   - [Models](#models)
   - [Tool Configuration](#tool-configuration)
   - [Cache-based Sessions](#cache-based-sessions)
   - [Views and Endpoints](#views-and-endpoints)
   - [Grade Passback Service](#grade-passback-service)
   - [Signals](#signals)
   - [Required Model Changes](#required-model-changes)
   - [URL Configuration](#url-configuration)
6. [Frontend Implementation](#frontend-implementation)
   - [Vue Components](#vue-components)
   - [Composables](#composables)
   - [Router Configuration](#router-configuration)
7. [Settings Configuration](#settings-configuration)
8. [Canvas Admin Setup](#canvas-admin-setup)
9. [Instructor Workflow](#instructor-workflow)
10. [Security Considerations](#security-considerations)
11. [Testing Guide](#testing-guide)
12. [Troubleshooting](#troubleshooting)

---

## Overview

### What is LTI?

LTI (Learning Tools Interoperability) is an IMS Global standard that enables secure integration between learning platforms (like Canvas) and external tools (like Purplex). LTI 1.3 uses OAuth 2.0 and OpenID Connect for authentication, providing cryptographic verification of user identity.

### Why LTI 1.3 over Simple Iframes?

| Feature | Simple Iframe | LTI 1.3 |
|---------|---------------|---------|
| Authentication | None or trust-based | Cryptographic (JWT signed by LMS) |
| User Identity | Can be spoofed | Verified, tamper-proof |
| Grade Passback | Manual | Automatic to LMS gradebook |
| Setup Complexity | Low | Medium |
| Security | Low | High |

### Key Features

- **Single-problem iframes** with cryptographically verified user identity
- **Automatic grade passback** to Canvas gradebook via LTI AGS
- **Deep linking** for instructors to select problems when creating assignments
- **Full submission tracking** linked to verified LMS users
- **Session management** optimized for iframe embedding

---

## Architecture

### Authentication Flow

```
┌─────────────────┐                              ┌─────────────────┐
│   Canvas LMS    │                              │    Purplex      │
└────────┬────────┘                              └────────┬────────┘
         │                                                │
         │  1. Student clicks assignment                  │
         │─────────────────────────────────────────────────>
         │     POST /lti/login/                           │
         │     (iss, login_hint, target_link_uri)         │
         │                                                │
         │<─────────────────────────────────────────────────
         │  2. Redirect to Canvas auth                    │
         │     (state, nonce)                             │
         │                                                │
         │  3. Canvas authenticates user                  │
         │─────────────────────────────────────────────────>
         │     POST /lti/launch/                          │
         │     (id_token - signed JWT with user info)     │
         │                                                │
         │                    4. Validate JWT signature   │
         │                    5. Create LTI session       │
         │                    6. Create/update LTI user   │
         │                                                │
         │<─────────────────────────────────────────────────
         │  7. Redirect to problem view                   │
         │     /lti/problem/{launch_id}/                  │
         │                                                │
         │  8. Student solves problem                     │
         │─────────────────────────────────────────────────>
         │     POST /lti/problem/{launch_id}/submit/      │
         │                                                │
         │                    9. Grade submission         │
         │                   10. Send grade to Canvas     │
         │<─────────────────────────────────────────────────
         │     LTI AGS: PUT score                         │
         │                                                │
         │<─────────────────────────────────────────────────
         │ 11. Show results                               │
```

### Deep Linking Flow (Assignment Creation)

```
┌─────────────────┐                              ┌─────────────────┐
│   Canvas LMS    │                              │    Purplex      │
└────────┬────────┘                              └────────┬────────┘
         │                                                │
         │  1. Instructor creates assignment              │
         │     Selects "External Tool" → "Purplex"        │
         │─────────────────────────────────────────────────>
         │     POST /lti/login/ (deep_link request)       │
         │                                                │
         │  [OIDC flow same as above]                     │
         │                                                │
         │<─────────────────────────────────────────────────
         │  2. Show problem selection UI                  │
         │                                                │
         │  3. Instructor selects problem                 │
         │─────────────────────────────────────────────────>
         │                                                │
         │<─────────────────────────────────────────────────
         │  4. Return deep link response                  │
         │     (content item with problem URL)            │
         │                                                │
         │  5. Canvas saves assignment config             │
```

---

## Dependencies

### Python Package

```bash
pip install PyLTI1p3>=2.0.0 jwcrypto>=1.5.0
```

**Add to `requirements.txt`:**
```
PyLTI1p3>=2.0.0
jwcrypto>=1.5.0  # Required for JWKS generation
cryptography>=41.0.0  # Already present, needed for RSA key generation
```

### PyLTI1p3 Features Used

- `DjangoOIDCLogin` - OIDC login initiation
- `DjangoMessageLaunch` - Launch message validation
- `Grade` - Grade submission to AGS
- `DeepLinkResource` - Deep linking responses

---

## Pre-Implementation Checklist

Before starting implementation, verify the following prerequisites are met:

### Infrastructure Requirements

- [ ] **HTTPS configured** - LTI 1.3 requires HTTPS for all endpoints
- [ ] **Redis running** - Required for cache-based sessions
- [ ] **PostgreSQL running** - For storing LTI models
- [ ] **Domain configured** - Public domain accessible from Canvas

### Code Prerequisites

- [ ] **Install dependencies**: Add PyLTI1p3 and jwcrypto to requirements.txt
- [ ] **Create lti app directory**: `mkdir -p purplex/lti/migrations purplex/lti/services purplex/lti/repositories purplex/lti/templates/lti`
- [ ] **Create `__init__.py` files** in all new directories
- [ ] **Add to INSTALLED_APPS**: Add `'purplex.lti'` to settings
- [ ] **Add middleware**: Add `'purplex.lti.cache_session.SessionCookieMiddleware'`
- [ ] **Update Submission model**: Add `lti_launch` ForeignKey field
- [ ] **Run migrations**: Create and apply LTI model migrations

### Canvas Requirements

- [ ] **Canvas admin access** - Needed to create Developer Keys
- [ ] **Test Canvas instance** - For development/testing (use Canvas Free-for-Teacher or a dev instance)

### Quick Start Commands

```bash
# 1. Install dependencies
pip install PyLTI1p3>=2.0.0 jwcrypto>=1.5.0

# 2. Create app structure
mkdir -p purplex/lti/{migrations,services,repositories,templates/lti}
touch purplex/lti/__init__.py
touch purplex/lti/migrations/__init__.py
touch purplex/lti/services/__init__.py
touch purplex/lti/repositories/__init__.py

# 3. Copy model, view, and config files from this guide

# 4. Run migrations
python manage.py makemigrations lti
python manage.py makemigrations submissions --name add_lti_launch_field
python manage.py migrate

# 5. Create platform record (after Canvas Developer Key setup)
python manage.py shell
```

---

## Backend Implementation

### Django App Structure

Create the following directory structure:

```
purplex/lti/
├── __init__.py
├── admin.py
├── apps.py
├── models.py
├── urls.py
├── views.py
├── tool_config.py
├── cache_session.py
├── middleware.py
├── services/
│   ├── __init__.py
│   └── grade_service.py
├── repositories/
│   ├── __init__.py
│   └── lti_repository.py
├── signals.py
├── migrations/
│   └── __init__.py
└── templates/
    └── lti/
        ├── problem.html
        ├── deep_link.html
        └── error.html
```

**File: `purplex/lti/apps.py`**

```python
from django.apps import AppConfig


class LtiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'purplex.lti'
    verbose_name = 'LTI Integration'

    def ready(self):
        # Import signals to register them
        from . import signals  # noqa: F401
```

**File: `purplex/lti/admin.py`**

```python
from django.contrib import admin
from .models import LTIPlatform, LTIDeployment, LTIUser, LTILaunch, LTIDeepLinkContent


@admin.register(LTIPlatform)
class LTIPlatformAdmin(admin.ModelAdmin):
    list_display = ['name', 'issuer', 'client_id', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name', 'issuer', 'client_id']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        (None, {
            'fields': ('name', 'issuer', 'client_id', 'is_active')
        }),
        ('OAuth Endpoints', {
            'fields': ('auth_login_url', 'auth_token_url', 'key_set_url')
        }),
        ('RSA Keys', {
            'fields': ('private_key', 'public_key'),
            'classes': ('collapse',),
            'description': 'RSA key pair for signing. Keep private key secret!'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(LTIDeployment)
class LTIDeploymentAdmin(admin.ModelAdmin):
    list_display = ['platform', 'deployment_id', 'created_at']
    list_filter = ['platform']
    search_fields = ['deployment_id', 'platform__name']


@admin.register(LTIUser)
class LTIUserAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'platform', 'purplex_user', 'launch_count', 'last_seen']
    list_filter = ['platform']
    search_fields = ['name', 'email', 'lti_user_id']
    readonly_fields = ['first_seen', 'last_seen', 'launch_count']


@admin.register(LTILaunch)
class LTILaunchAdmin(admin.ModelAdmin):
    list_display = ['launch_id_short', 'lti_user', 'problem', 'context_title', 'grade_submitted', 'created_at']
    list_filter = ['platform', 'is_deep_link', 'grade_submitted']
    search_fields = ['launch_id', 'lti_user__name', 'problem__title']
    readonly_fields = ['launch_id', 'created_at', 'expires_at', 'launch_data']
    date_hierarchy = 'created_at'

    def launch_id_short(self, obj):
        return f"{obj.launch_id[:12]}..."
    launch_id_short.short_description = 'Launch ID'


@admin.register(LTIDeepLinkContent)
class LTIDeepLinkContentAdmin(admin.ModelAdmin):
    list_display = ['problem', 'created_by', 'context_title', 'created_at']
    list_filter = ['platform']
    search_fields = ['problem__title', 'context_title']
```

### Models

**File: `purplex/lti/models.py`**

```python
"""
LTI 1.3 Models for Canvas Integration

These models store LTI platform configurations, track launches, and manage
LMS user identities for embedded problem submissions.
"""

import secrets
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


class LTIPlatform(models.Model):
    """
    LMS Platform configuration (e.g., a Canvas instance).

    Each Canvas instance that integrates with Purplex needs one of these records.
    Contains the OAuth/OIDC configuration for authenticating launches.
    """

    # Human-readable name for admin interface
    name = models.CharField(
        max_length=255,
        help_text="Display name, e.g., 'University of Example Canvas'"
    )

    # Canvas instance URL - must match 'iss' claim in JWT
    issuer = models.CharField(
        max_length=500,
        unique=True,
        db_index=True,
        help_text="Canvas instance URL, e.g., 'https://canvas.university.edu'"
    )

    # Client ID from Canvas Developer Key
    client_id = models.CharField(
        max_length=255,
        help_text="Client ID from Canvas Developer Key"
    )

    # Canvas OIDC/OAuth endpoints
    auth_login_url = models.URLField(
        help_text="Canvas OIDC authorization URL"
    )
    auth_token_url = models.URLField(
        help_text="Canvas OAuth token URL"
    )
    key_set_url = models.URLField(
        help_text="Canvas JWKS URL for verifying signatures"
    )

    # Our tool's RSA keys for signing
    # IMPORTANT: In production, store private_key encrypted or in secrets manager
    private_key = models.TextField(
        help_text="RSA private key (PEM format) for signing requests"
    )
    public_key = models.TextField(
        help_text="RSA public key (PEM format) exposed via JWKS endpoint"
    )

    # Status
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this platform is enabled for launches"
    )

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'lti'
        verbose_name = 'LTI Platform'
        verbose_name_plural = 'LTI Platforms'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.issuer})"

    @classmethod
    def generate_rsa_keys(cls):
        """Generate a new RSA key pair for a platform."""
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.backends import default_backend

        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )

        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode('utf-8')

        public_pem = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')

        return private_pem, public_pem


class LTIDeployment(models.Model):
    """
    Deployment of tool within a platform.

    A single Canvas instance can have multiple deployments (e.g., different
    courses or sub-accounts). Each deployment has a unique ID.
    """

    platform = models.ForeignKey(
        LTIPlatform,
        on_delete=models.CASCADE,
        related_name='deployments'
    )
    deployment_id = models.CharField(
        max_length=255,
        help_text="Deployment ID from Canvas"
    )

    # Optional: restrict to specific courses
    allowed_context_ids = models.JSONField(
        default=list,
        blank=True,
        help_text="List of Canvas context IDs allowed for this deployment"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'lti'
        unique_together = ['platform', 'deployment_id']
        verbose_name = 'LTI Deployment'
        verbose_name_plural = 'LTI Deployments'

    def __str__(self):
        return f"{self.platform.name} - {self.deployment_id}"


class LTIUser(models.Model):
    """
    LMS user with verified identity.

    Tracks users who access Purplex via LTI launches. These users may not have
    Purplex accounts - their identity is verified by Canvas.
    """

    platform = models.ForeignKey(
        LTIPlatform,
        on_delete=models.CASCADE,
        related_name='users'
    )

    # Canvas user ID (sub claim from JWT)
    lti_user_id = models.CharField(
        max_length=255,
        db_index=True,
        help_text="User ID from Canvas (sub claim)"
    )

    # Optional link to Purplex account (for users who have both)
    purplex_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='lti_identities',
        help_text="Linked Purplex account (optional)"
    )

    # Cached user info from Canvas
    name = models.CharField(
        max_length=255,
        blank=True,
        help_text="Display name from Canvas"
    )
    email = models.CharField(
        max_length=255,
        blank=True,
        help_text="Email from Canvas"
    )

    # Canvas-provided roles (for analytics)
    roles = models.JSONField(
        default=list,
        help_text="LTI roles from most recent launch"
    )

    # Tracking
    first_seen = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)
    launch_count = models.PositiveIntegerField(default=0)

    class Meta:
        app_label = 'lti'
        unique_together = ['platform', 'lti_user_id']
        verbose_name = 'LTI User'
        verbose_name_plural = 'LTI Users'
        indexes = [
            models.Index(fields=['platform', 'lti_user_id']),
            models.Index(fields=['email']),
        ]

    def __str__(self):
        return f"{self.name or self.lti_user_id} ({self.platform.name})"

    @property
    def is_instructor(self):
        """Check if user has instructor role based on LTI roles."""
        instructor_roles = [
            'http://purl.imsglobal.org/vocab/lis/v2/membership#Instructor',
            'http://purl.imsglobal.org/vocab/lis/v2/institution/person#Instructor',
        ]
        return any(role in self.roles for role in instructor_roles)


class LTILaunch(models.Model):
    """
    Record of each LTI launch session.

    Created when a user launches into Purplex from Canvas. Contains all the
    context needed to render the problem and submit grades back.
    """

    # Unique session identifier
    launch_id = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        help_text="Unique session token for this launch"
    )

    # Platform and user
    platform = models.ForeignKey(
        LTIPlatform,
        on_delete=models.CASCADE,
        related_name='launches'
    )
    lti_user = models.ForeignKey(
        LTIUser,
        on_delete=models.CASCADE,
        related_name='launches'
    )

    # Canvas context
    context_id = models.CharField(
        max_length=255,
        blank=True,
        db_index=True,
        help_text="Canvas course/context ID"
    )
    context_title = models.CharField(
        max_length=255,
        blank=True,
        help_text="Canvas course name"
    )
    resource_link_id = models.CharField(
        max_length=255,
        blank=True,
        help_text="Canvas assignment/resource link ID"
    )
    resource_link_title = models.CharField(
        max_length=255,
        blank=True,
        help_text="Canvas assignment name"
    )

    # Problem being accessed
    problem = models.ForeignKey(
        'problems_app.Problem',
        on_delete=models.CASCADE,
        related_name='lti_launches'
    )

    # Assignment and Grades Service (AGS) configuration
    # These URLs are used to submit grades back to Canvas
    ags_endpoint = models.URLField(
        blank=True,
        help_text="AGS endpoint URL for grade submission"
    )
    ags_lineitem = models.URLField(
        blank=True,
        help_text="Specific lineitem URL for this assignment"
    )
    ags_scope = models.JSONField(
        default=list,
        help_text="AGS scopes granted for this launch"
    )

    # Names and Roles Provisioning Service (NRPS) - optional
    nrps_endpoint = models.URLField(
        blank=True,
        help_text="NRPS endpoint for roster access"
    )

    # User info snapshot at launch time
    user_name = models.CharField(max_length=255, blank=True)
    user_email = models.CharField(max_length=255, blank=True)
    user_roles = models.JSONField(default=list)

    # Launch message data (for reconstructing message_launch)
    launch_data = models.JSONField(
        default=dict,
        help_text="Full JWT claims for reference"
    )

    # Session management
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(
        help_text="Session expiration time"
    )

    # State tracking
    is_deep_link = models.BooleanField(
        default=False,
        help_text="Whether this was a deep linking launch"
    )
    grade_submitted = models.BooleanField(
        default=False,
        help_text="Whether grade has been sent to Canvas"
    )
    last_grade_score = models.FloatField(
        null=True,
        blank=True,
        help_text="Last grade submitted (0-1 scale)"
    )
    last_grade_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When last grade was submitted"
    )

    class Meta:
        app_label = 'lti'
        verbose_name = 'LTI Launch'
        verbose_name_plural = 'LTI Launches'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['launch_id']),
            models.Index(fields=['platform', 'context_id']),
            models.Index(fields=['lti_user', '-created_at']),
            models.Index(fields=['problem', '-created_at']),
        ]

    def __str__(self):
        return f"Launch {self.launch_id[:8]}... - {self.problem.slug}"

    @classmethod
    def generate_launch_id(cls):
        """Generate a unique launch ID."""
        return secrets.token_urlsafe(48)

    @property
    def is_expired(self):
        """Check if this launch session has expired."""
        return timezone.now() > self.expires_at

    @property
    def can_submit_grade(self):
        """Check if grade submission is possible for this launch."""
        return bool(self.ags_lineitem) and not self.is_expired

    def save(self, *args, **kwargs):
        if not self.launch_id:
            self.launch_id = self.generate_launch_id()
        if not self.expires_at:
            # Default: 4 hour session
            self.expires_at = timezone.now() + timedelta(hours=4)
        super().save(*args, **kwargs)


class LTIDeepLinkContent(models.Model):
    """
    Tracks deep link content items created by instructors.

    When an instructor selects a problem via deep linking, we record it here
    for analytics and troubleshooting.
    """

    platform = models.ForeignKey(
        LTIPlatform,
        on_delete=models.CASCADE,
        related_name='deep_link_content'
    )

    # The instructor who created this
    created_by = models.ForeignKey(
        LTIUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_deep_links'
    )

    # Canvas context
    context_id = models.CharField(max_length=255, blank=True)
    context_title = models.CharField(max_length=255, blank=True)

    # Problem selected
    problem = models.ForeignKey(
        'problems_app.Problem',
        on_delete=models.CASCADE,
        related_name='deep_links'
    )

    # Custom settings for this deep link
    custom_params = models.JSONField(
        default=dict,
        help_text="Custom parameters passed to launches"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'lti'
        verbose_name = 'LTI Deep Link Content'
        verbose_name_plural = 'LTI Deep Link Contents'
```

### Tool Configuration

**File: `purplex/lti/tool_config.py`**

```python
"""
PyLTI1p3 Tool Configuration from Django Database

This module provides a custom tool configuration class that loads LTI platform
settings from Django models instead of JSON files.
"""

from pylti1p3.tool_config import ToolConfAbstract
from .models import LTIPlatform, LTIDeployment


class DjangoDbToolConf(ToolConfAbstract):
    """
    Load LTI configuration from Django database models.

    PyLTI1p3 uses this to look up platform settings when validating launches.
    """

    _platforms_cache = {}

    def find_registration_by_issuer(self, iss, *args, **kwargs):
        """
        Find platform registration by issuer URL.

        Args:
            iss: The issuer URL from the JWT (Canvas instance URL)

        Returns:
            Registration dict or None if not found
        """
        # Check cache first
        if iss in self._platforms_cache:
            platform = self._platforms_cache[iss]
        else:
            try:
                platform = LTIPlatform.objects.prefetch_related(
                    'deployments'
                ).get(issuer=iss, is_active=True)
                self._platforms_cache[iss] = platform
            except LTIPlatform.DoesNotExist:
                return None

        return self._platform_to_registration(platform)

    def find_registration_by_params(self, iss, client_id, *args, **kwargs):
        """
        Find platform registration by issuer and client_id.

        Some LTI operations require both to identify the platform.
        """
        try:
            platform = LTIPlatform.objects.prefetch_related(
                'deployments'
            ).get(
                issuer=iss,
                client_id=client_id,
                is_active=True
            )
            return self._platform_to_registration(platform)
        except LTIPlatform.DoesNotExist:
            return None

    def find_deployment(self, iss, deployment_id):
        """
        Verify a deployment ID is valid for a platform.

        Args:
            iss: The issuer URL
            deployment_id: The deployment ID from the launch

        Returns:
            Deployment dict or None
        """
        try:
            deployment = LTIDeployment.objects.select_related(
                'platform'
            ).get(
                platform__issuer=iss,
                platform__is_active=True,
                deployment_id=deployment_id
            )
            return {'deployment_id': deployment.deployment_id}
        except LTIDeployment.DoesNotExist:
            return None

    def find_deployment_by_params(self, iss, deployment_id, client_id, *args, **kwargs):
        """Find deployment with full parameter validation."""
        try:
            deployment = LTIDeployment.objects.select_related(
                'platform'
            ).get(
                platform__issuer=iss,
                platform__client_id=client_id,
                platform__is_active=True,
                deployment_id=deployment_id
            )
            return {'deployment_id': deployment.deployment_id}
        except LTIDeployment.DoesNotExist:
            return None

    def _platform_to_registration(self, platform: LTIPlatform) -> dict:
        """
        Convert a LTIPlatform model to PyLTI1p3 registration format.
        """
        deployment_ids = list(
            platform.deployments.values_list('deployment_id', flat=True)
        )

        return {
            'issuer': platform.issuer,
            'client_id': platform.client_id,
            'auth_login_url': platform.auth_login_url,
            'auth_token_url': platform.auth_token_url,
            'key_set_url': platform.key_set_url,
            'private_key_file': platform.private_key,
            'public_key_file': platform.public_key,
            'deployment_ids': deployment_ids,
        }

    def get_jwks(self, iss=None, client_id=None, **kwargs):
        """
        Get JWKS (JSON Web Key Set) for a platform or all platforms.

        This is called when generating the /lti/jwks/ response.
        """
        from jwcrypto import jwk

        keys = []

        if iss:
            platforms = LTIPlatform.objects.filter(issuer=iss, is_active=True)
        else:
            platforms = LTIPlatform.objects.filter(is_active=True)

        for platform in platforms:
            try:
                key = jwk.JWK.from_pem(platform.public_key.encode('utf-8'))
                key_dict = key.export(as_dict=True)
                key_dict['use'] = 'sig'
                key_dict['alg'] = 'RS256'
                keys.append(key_dict)
            except Exception:
                continue

        return {'keys': keys}

    @classmethod
    def clear_cache(cls):
        """Clear the platform cache (call after updating platforms)."""
        cls._platforms_cache = {}
```

### Cache-based Sessions

**File: `purplex/lti/cache_session.py`**

```python
"""
Cache-based Session Service for LTI 1.3

Standard Django sessions don't work well in iframes due to SameSite cookie
restrictions. This implementation uses Django's cache backend (Redis) to
store session data with a custom cookie that has the necessary attributes.
"""

import secrets
from typing import Any, Optional

from django.core.cache import cache
from pylti1p3.session import SessionService


class DjangoCacheSession(SessionService):
    """
    Use Django cache backend for LTI session storage.

    This solves iframe session issues by:
    1. Using a separate cookie from Django's session cookie
    2. Setting SameSite=None and Secure attributes
    3. Storing data in Redis (cache) instead of cookie
    """

    CACHE_PREFIX = 'lti:session:'
    CACHE_TIMEOUT = 3600  # 1 hour
    COOKIE_NAME = 'lti1p3_session'

    def __init__(self, request):
        """
        Initialize session service.

        Args:
            request: Django HTTP request object
        """
        self._request = request
        self._session_id = None
        self._cookie_service = None

        # Try to get existing session ID from cookie
        self._session_id = request.COOKIES.get(self.COOKIE_NAME)

        # Generate new session ID if needed
        if not self._session_id:
            self._session_id = self._generate_session_id()
            self._is_new_session = True
        else:
            self._is_new_session = False

    def _generate_session_id(self) -> str:
        """Generate a cryptographically secure session ID."""
        return secrets.token_urlsafe(32)

    def _get_cache_key(self, key: str) -> str:
        """Generate cache key for session data."""
        return f"{self.CACHE_PREFIX}{self._session_id}:{key}"

    def get_launch_data(self, key: str) -> Optional[Any]:
        """
        Retrieve launch data from cache.

        Args:
            key: The data key (e.g., 'lti1p3-launch-id')

        Returns:
            The stored data or None
        """
        return cache.get(self._get_cache_key(key))

    def save_launch_data(self, key: str, value: Any) -> None:
        """
        Save launch data to cache.

        Args:
            key: The data key
            value: The data to store
        """
        cache.set(
            self._get_cache_key(key),
            value,
            timeout=self.CACHE_TIMEOUT
        )

    def check_state_is_valid(self, state: str, id_token_hash: str) -> bool:
        """
        Validate the state parameter from OIDC callback.

        Args:
            state: State parameter from callback
            id_token_hash: Hash of the id_token

        Returns:
            True if state is valid
        """
        stored_state = self.get_launch_data('state')
        if not stored_state:
            return False
        return stored_state == state

    def save_state_params(self, state: str, params: dict) -> None:
        """Save state parameters for OIDC flow."""
        self.save_launch_data('state', state)
        self.save_launch_data('state_params', params)

    def get_state_params(self, state: str) -> Optional[dict]:
        """Get saved state parameters."""
        stored_state = self.get_launch_data('state')
        if stored_state != state:
            return None
        return self.get_launch_data('state_params')

    def get_session_id(self) -> str:
        """Get the current session ID."""
        return self._session_id

    def is_new_session(self) -> bool:
        """Check if this is a new session."""
        return self._is_new_session

    def set_session_cookie(self, response):
        """
        Set the session cookie on the response.

        Call this on every LTI response to maintain the session.

        Args:
            response: Django HTTP response object
        """
        response.set_cookie(
            self.COOKIE_NAME,
            self._session_id,
            max_age=self.CACHE_TIMEOUT,
            secure=True,  # Required for SameSite=None
            httponly=True,
            samesite='None',  # Required for iframe
        )
        return response


class SessionCookieMiddleware:
    """
    Middleware to handle LTI session cookies.

    This ensures the session cookie is set on all LTI responses.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Only process LTI routes
        if request.path.startswith('/lti/'):
            if hasattr(request, '_lti_session'):
                request._lti_session.set_session_cookie(response)

        return response
```

### Views and Endpoints

**File: `purplex/lti/views.py`**

```python
"""
LTI 1.3 Views

Implements the OIDC login, launch, JWKS, and deep linking endpoints
required for LTI 1.3 tool integration.
"""

import json
import secrets
from datetime import timedelta

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from pylti1p3.contrib.django import DjangoOIDCLogin, DjangoMessageLaunch
from pylti1p3.deep_link_resource import DeepLinkResource
from pylti1p3.exception import LtiException

from purplex.problems_app.models import Problem

from .cache_session import DjangoCacheSession
from .models import LTIDeepLinkContent, LTILaunch, LTIPlatform, LTIUser
from .tool_config import DjangoDbToolConf


@method_decorator(csrf_exempt, name='dispatch')
class OIDCLoginView(View):
    """
    LTI 1.3 OIDC Login Initiation Endpoint.

    Step 1 of the LTI launch flow. Canvas sends the user here to initiate
    authentication. We redirect to Canvas's authorization endpoint.

    URL: /lti/login/
    Methods: GET, POST (Canvas uses POST)
    """

    def get(self, request):
        return self._handle_login(request)

    def post(self, request):
        return self._handle_login(request)

    def _handle_login(self, request):
        """Process OIDC login initiation request."""
        tool_conf = DjangoDbToolConf()
        session_service = DjangoCacheSession(request)
        request._lti_session = session_service

        try:
            oidc_login = DjangoOIDCLogin(
                request,
                tool_conf,
                session_service=session_service
            )

            # Build target URL (where Canvas should redirect after auth)
            target_link_uri = request.POST.get(
                'target_link_uri',
                request.GET.get('target_link_uri')
            )

            if not target_link_uri:
                target_link_uri = request.build_absolute_uri(
                    reverse('lti_launch')
                )

            # Redirect to Canvas authorization
            response = oidc_login.redirect(target_link_uri)

            # Set session cookie
            session_service.set_session_cookie(response)

            return response

        except LtiException as e:
            return render(request, 'lti/error.html', {
                'error': 'Login initialization failed',
                'details': str(e)
            }, status=400)


@method_decorator(csrf_exempt, name='dispatch')
class LTILaunchView(View):
    """
    LTI 1.3 Launch Callback Endpoint.

    Step 2 of the LTI launch flow. Canvas redirects here after authentication
    with a signed JWT containing user info. We validate and create a session.

    URL: /lti/launch/
    Methods: POST
    """

    def post(self, request):
        tool_conf = DjangoDbToolConf()
        session_service = DjangoCacheSession(request)
        request._lti_session = session_service

        try:
            message_launch = DjangoMessageLaunch(
                request,
                tool_conf,
                session_service=session_service
            )

            # Validate JWT signature and claims
            message_launch.validate()

            # Extract launch data from JWT
            launch_data = message_launch.get_launch_data()

            # Get or create platform
            platform = LTIPlatform.objects.get(
                issuer=launch_data['iss'],
                is_active=True
            )

            # Get or create LTI user
            lti_user, created = LTIUser.objects.update_or_create(
                platform=platform,
                lti_user_id=launch_data['sub'],
                defaults={
                    'name': launch_data.get('name', ''),
                    'email': launch_data.get('email', ''),
                    'roles': launch_data.get(
                        'https://purl.imsglobal.org/spec/lti/claim/roles',
                        []
                    ),
                }
            )

            # Increment launch count
            from django.db.models import F
            LTIUser.objects.filter(pk=lti_user.pk).update(
                launch_count=F('launch_count') + 1,
                last_seen=timezone.now()
            )

            # Check for deep linking request
            if message_launch.is_deep_link_launch():
                return self._handle_deep_link_launch(
                    request, message_launch, platform, lti_user, launch_data
                )

            # Regular resource launch
            return self._handle_resource_launch(
                request, message_launch, platform, lti_user, launch_data
            )

        except LtiException as e:
            return render(request, 'lti/error.html', {
                'error': 'Launch validation failed',
                'details': str(e)
            }, status=400)
        except Problem.DoesNotExist:
            return render(request, 'lti/error.html', {
                'error': 'Problem not found',
                'details': 'The requested problem could not be found.'
            }, status=404)

    def _handle_resource_launch(
        self, request, message_launch, platform, lti_user, launch_data
    ):
        """Handle a regular resource link launch (student viewing problem)."""

        # Extract problem from custom parameters or resource link
        custom_claims = launch_data.get(
            'https://purl.imsglobal.org/spec/lti/claim/custom',
            {}
        )
        problem_slug = custom_claims.get('problem_slug')

        if not problem_slug:
            # Try to get from resource link title
            resource_link = launch_data.get(
                'https://purl.imsglobal.org/spec/lti/claim/resource_link',
                {}
            )
            problem_slug = resource_link.get('title', '').lower().replace(' ', '-')

        problem = get_object_or_404(Problem, slug=problem_slug, is_active=True)

        # Extract context info
        context_claim = launch_data.get(
            'https://purl.imsglobal.org/spec/lti/claim/context',
            {}
        )
        resource_link = launch_data.get(
            'https://purl.imsglobal.org/spec/lti/claim/resource_link',
            {}
        )

        # Extract AGS info for grade passback
        ags_claim = launch_data.get(
            'https://purl.imsglobal.org/spec/lti-ags/claim/endpoint',
            {}
        )

        # Create launch record
        launch = LTILaunch.objects.create(
            platform=platform,
            lti_user=lti_user,
            problem=problem,
            context_id=context_claim.get('id', ''),
            context_title=context_claim.get('title', ''),
            resource_link_id=resource_link.get('id', ''),
            resource_link_title=resource_link.get('title', ''),
            user_name=launch_data.get('name', ''),
            user_email=launch_data.get('email', ''),
            user_roles=launch_data.get(
                'https://purl.imsglobal.org/spec/lti/claim/roles',
                []
            ),
            ags_endpoint=ags_claim.get('lineitems', ''),
            ags_lineitem=ags_claim.get('lineitem', ''),
            ags_scope=ags_claim.get('scope', []),
            launch_data=launch_data,
            expires_at=timezone.now() + timedelta(hours=4),
        )

        # Store launch ID in session for the message_launch reconstruction
        session_service = request._lti_session
        session_service.save_launch_data('launch_id', launch.launch_id)
        session_service.save_launch_data('message_launch', message_launch.get_launch_data())

        # Redirect to problem view
        response = redirect('lti_problem', launch_id=launch.launch_id)
        session_service.set_session_cookie(response)
        return response

    def _handle_deep_link_launch(
        self, request, message_launch, platform, lti_user, launch_data
    ):
        """Handle a deep linking launch (instructor selecting problem)."""

        context_claim = launch_data.get(
            'https://purl.imsglobal.org/spec/lti/claim/context',
            {}
        )

        # Create a temporary launch for the deep link session
        launch = LTILaunch.objects.create(
            platform=platform,
            lti_user=lti_user,
            problem_id=1,  # Placeholder, will be updated
            context_id=context_claim.get('id', ''),
            context_title=context_claim.get('title', ''),
            user_name=launch_data.get('name', ''),
            user_email=launch_data.get('email', ''),
            user_roles=launch_data.get(
                'https://purl.imsglobal.org/spec/lti/claim/roles',
                []
            ),
            launch_data=launch_data,
            is_deep_link=True,
            expires_at=timezone.now() + timedelta(hours=1),
        )

        # Store for deep link handling
        session_service = request._lti_session
        session_service.save_launch_data('deep_link_launch_id', launch.launch_id)
        session_service.save_launch_data('message_launch', message_launch.get_launch_data())

        # Redirect to deep link selection UI
        response = redirect('lti_deep_link', launch_id=launch.launch_id)
        session_service.set_session_cookie(response)
        return response


class JWKSView(View):
    """
    JSON Web Key Set Endpoint.

    Canvas fetches our public keys from here to verify our signed messages.

    URL: /lti/jwks/
    Methods: GET
    """

    def get(self, request):
        tool_conf = DjangoDbToolConf()
        jwks = tool_conf.get_jwks()
        return JsonResponse(jwks)


class LTIProblemView(View):
    """
    Problem View for LTI-launched Sessions.

    Renders the problem solving interface for a valid LTI launch session.

    URL: /lti/problem/<launch_id>/
    Methods: GET
    """

    def get(self, request, launch_id):
        launch = get_object_or_404(
            LTILaunch.objects.select_related('problem', 'lti_user', 'platform'),
            launch_id=launch_id
        )

        if launch.is_expired:
            return render(request, 'lti/error.html', {
                'error': 'Session Expired',
                'details': 'Your session has expired. Please return to Canvas and relaunch the activity.'
            }, status=403)

        # For SPA: pass data to Vue app
        context = {
            'launch': launch,
            'problem': launch.problem,
            'user_name': launch.user_name,
            'launch_data_json': json.dumps({
                'launch_id': launch.launch_id,
                'problem_slug': launch.problem.slug,
                'problem_title': launch.problem.title,
                'user_name': launch.user_name,
                'context_title': launch.context_title,
                'can_submit_grade': launch.can_submit_grade,
            }),
        }

        return render(request, 'lti/problem.html', context)


@method_decorator(csrf_exempt, name='dispatch')
class LTISubmitView(View):
    """
    Submission Endpoint for LTI Context.

    Handles problem submissions from LTI-launched sessions.
    Triggers grade passback on completion.

    URL: /lti/problem/<launch_id>/submit/
    Methods: POST
    """

    def post(self, request, launch_id):
        launch = get_object_or_404(
            LTILaunch.objects.select_related('problem', 'lti_user'),
            launch_id=launch_id
        )

        if launch.is_expired:
            return JsonResponse({
                'error': 'Session expired',
                'details': 'Please return to Canvas and relaunch.'
            }, status=403)

        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        raw_input = data.get('raw_input', '').strip()
        if not raw_input:
            return JsonResponse({'error': 'Input required'}, status=400)

        # Import here to avoid circular imports
        from purplex.problems_app.views.submission_views import process_submission

        # Process submission with LTI context
        result = process_submission(
            problem=launch.problem,
            raw_input=raw_input,
            user=launch.lti_user.purplex_user,  # May be None
            lti_launch=launch,
            lti_user=launch.lti_user,
        )

        return JsonResponse(result)


class DeepLinkView(View):
    """
    Deep Linking Selection Interface.

    Shows instructors a list of available problems to select for assignment.

    URL: /lti/deep-link/<launch_id>/
    Methods: GET, POST
    """

    def get(self, request, launch_id):
        """Show problem selection interface."""
        launch = get_object_or_404(
            LTILaunch.objects.select_related('platform', 'lti_user'),
            launch_id=launch_id,
            is_deep_link=True
        )

        if launch.is_expired:
            return render(request, 'lti/error.html', {
                'error': 'Session Expired'
            }, status=403)

        # Get available problems
        problems = Problem.objects.filter(is_active=True).order_by('title')

        return render(request, 'lti/deep_link.html', {
            'launch': launch,
            'problems': problems,
        })

    def post(self, request, launch_id):
        """Handle problem selection and return to Canvas."""
        launch = get_object_or_404(
            LTILaunch.objects.select_related('platform', 'lti_user'),
            launch_id=launch_id,
            is_deep_link=True
        )

        if launch.is_expired:
            return JsonResponse({'error': 'Session expired'}, status=403)

        problem_slug = request.POST.get('problem_slug')
        problem = get_object_or_404(Problem, slug=problem_slug, is_active=True)

        # Get session and reconstruct message launch
        session_service = DjangoCacheSession(request)
        launch_data = session_service.get_launch_data('message_launch')

        if not launch_data:
            return render(request, 'lti/error.html', {
                'error': 'Session data lost'
            }, status=400)

        tool_conf = DjangoDbToolConf()

        # Create message launch from stored data
        message_launch = DjangoMessageLaunch(
            request,
            tool_conf,
            session_service=session_service
        )
        message_launch.set_launch_data(launch_data)

        # Build deep link resource
        resource = DeepLinkResource()
        resource.set_url(
            request.build_absolute_uri(reverse('lti_launch'))
        )
        resource.set_custom_params({
            'problem_slug': problem.slug,
        })
        resource.set_title(problem.title)

        # Record the deep link
        LTIDeepLinkContent.objects.create(
            platform=launch.platform,
            created_by=launch.lti_user,
            context_id=launch.context_id,
            context_title=launch.context_title,
            problem=problem,
            custom_params={'problem_slug': problem.slug},
        )

        # Get the deep link return response
        deep_link = message_launch.get_deep_link()
        response_html = deep_link.output_response_form([resource])

        return HttpResponse(response_html)
```

### Grade Passback Service

**File: `purplex/lti/services/grade_service.py`**

```python
"""
LTI Assignment and Grades Service (AGS) Integration

Handles submitting grades back to Canvas gradebook after students complete
problems.
"""

import logging
from typing import Optional

from django.utils import timezone

from pylti1p3.grade import Grade
from pylti1p3.contrib.django import DjangoMessageLaunch

from ..cache_session import DjangoCacheSession
from ..models import LTILaunch
from ..tool_config import DjangoDbToolConf

logger = logging.getLogger(__name__)


class LTIGradeService:
    """
    Service for submitting grades to Canvas via LTI AGS.

    Canvas uses the Assignment and Grades Service (AGS) to allow tools to
    write grades directly to the gradebook.
    """

    def __init__(self, launch: LTILaunch):
        """
        Initialize grade service for a launch.

        Args:
            launch: The LTI launch record with AGS info
        """
        self.launch = launch
        self.tool_conf = DjangoDbToolConf()

    def can_submit_grade(self) -> bool:
        """Check if grade submission is possible."""
        return (
            bool(self.launch.ags_lineitem) and
            not self.launch.is_expired and
            'https://purl.imsglobal.org/spec/lti-ags/scope/score' in self.launch.ags_scope
        )

    def submit_score(
        self,
        score: float,
        max_score: float = 100.0,
        comment: Optional[str] = None,
        activity_progress: str = 'Completed',
        grading_progress: str = 'FullyGraded'
    ) -> bool:
        """
        Submit a score to Canvas gradebook.

        Args:
            score: The student's score (0 to max_score)
            max_score: Maximum possible score (default 100)
            comment: Optional feedback comment
            activity_progress: Student's progress status
                - 'Initialized': Started but not submitted
                - 'Started': In progress
                - 'InProgress': Actively working
                - 'Submitted': Submitted for grading
                - 'Completed': Fully completed
            grading_progress: Grading status
                - 'FullyGraded': Final grade
                - 'Pending': Awaiting grading
                - 'PendingManual': Needs manual review
                - 'Failed': Grading failed
                - 'NotReady': Not ready to grade

        Returns:
            True if grade was submitted successfully
        """
        if not self.can_submit_grade():
            logger.warning(
                f"Cannot submit grade for launch {self.launch.launch_id}: "
                f"AGS not available or session expired"
            )
            return False

        try:
            # Reconstruct message launch from stored data
            message_launch = self._get_message_launch()

            if not message_launch or not message_launch.has_ags():
                logger.error(
                    f"Cannot get AGS for launch {self.launch.launch_id}"
                )
                return False

            ags = message_launch.get_ags()

            # Build grade object
            grade = Grade()
            grade.set_score_given(score)
            grade.set_score_maximum(max_score)
            grade.set_activity_progress(activity_progress)
            grade.set_grading_progress(grading_progress)
            grade.set_user_id(self.launch.lti_user.lti_user_id)
            grade.set_timestamp(timezone.now().isoformat())

            if comment:
                grade.set_comment(comment)

            # Submit to Canvas
            ags.put_grade(grade)

            # Update launch record
            self.launch.grade_submitted = True
            self.launch.last_grade_score = score / max_score
            self.launch.last_grade_at = timezone.now()
            self.launch.save(update_fields=[
                'grade_submitted',
                'last_grade_score',
                'last_grade_at'
            ])

            logger.info(
                f"Grade submitted for launch {self.launch.launch_id}: "
                f"{score}/{max_score}"
            )
            return True

        except Exception as e:
            logger.exception(
                f"Failed to submit grade for launch {self.launch.launch_id}: {e}"
            )
            return False

    def _get_message_launch(self) -> Optional[DjangoMessageLaunch]:
        """
        Reconstruct the message launch from stored data.

        We need this to access the AGS service with proper authentication.
        """
        # Create a mock request-like object for session service
        class MockRequest:
            COOKIES = {}

        mock_request = MockRequest()
        session_service = DjangoCacheSession(mock_request)

        # Try to get launch data from the launch record
        launch_data = self.launch.launch_data

        if not launch_data:
            return None

        try:
            message_launch = DjangoMessageLaunch.from_cache(
                self.launch.launch_id,
                request=mock_request,
                tool_config=self.tool_conf,
                session_service=session_service
            )
            return message_launch
        except Exception:
            # Fall back to creating from stored data
            message_launch = DjangoMessageLaunch(
                mock_request,
                self.tool_conf,
                session_service=session_service
            )
            message_launch.set_launch_data(launch_data)
            return message_launch


def submit_grade_for_submission(submission) -> bool:
    """
    Convenience function to submit grade for a submission.

    Args:
        submission: A Submission model instance with lti_launch field
                   (requires model migration - see signals.py notes)

    Returns:
        True if grade was submitted (or not needed)
    """
    # Check if lti_launch field exists and is set
    if not hasattr(submission, 'lti_launch') or not submission.lti_launch:
        return True  # No LTI context, nothing to do

    grade_service = LTIGradeService(submission.lti_launch)

    if not grade_service.can_submit_grade():
        return True  # Can't submit, but not an error

    # Build comment based on submission
    comment = f"Purplex submission - {submission.completion_status}"
    if submission.comprehension_level and submission.comprehension_level != 'not_evaluated':
        comment += f" ({submission.comprehension_level})"

    return grade_service.submit_score(
        score=submission.score,
        max_score=100,
        comment=comment,
        activity_progress='Completed' if submission.score > 0 else 'Submitted',
        grading_progress='FullyGraded'
    )
```

### Signals

**File: `purplex/lti/signals.py`**

> **Note**: This signal requires adding an `lti_launch` ForeignKey field to the `Submission` model. See the Model Changes section below.

```python
"""
Django Signals for LTI Integration

Automatically trigger grade submission when submissions complete.

IMPORTANT: Before using this signal, add to purplex/submissions/models.py:

    # Add to Submission model
    lti_launch = models.ForeignKey(
        'lti.LTILaunch',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='submissions',
        help_text="LTI launch context if submitted via LMS"
    )
"""

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from purplex.submissions.models import Submission

from .services.grade_service import submit_grade_for_submission

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Submission)
def send_lti_grade_on_completion(sender, instance, created, **kwargs):
    """
    Submit grade to Canvas when a submission completes.

    This signal fires after every Submission save. We only submit grades
    when the submission is in a completed state and has an LTI context.
    """
    # Only process completed submissions
    if instance.execution_status not in ('completed', 'failed'):
        return

    # Only process if there's an LTI launch (check for field existence first)
    if not hasattr(instance, 'lti_launch') or not instance.lti_launch:
        return

    # Don't re-submit if grade already sent
    if instance.lti_launch.grade_submitted:
        # Only update if score improved
        if instance.score <= (instance.lti_launch.last_grade_score or 0) * 100:
            return

    # Submit grade asynchronously to avoid blocking
    try:
        success = submit_grade_for_submission(instance)
        if success:
            logger.info(
                f"LTI grade submitted for submission {instance.submission_id}"
            )
        else:
            logger.warning(
                f"Failed to submit LTI grade for submission {instance.submission_id}"
            )
    except Exception as e:
        logger.exception(
            f"Error submitting LTI grade for submission {instance.submission_id}: {e}"
        )
```

### Required Model Changes

Before implementing LTI support, you must add the `lti_launch` field to the `Submission` model in `purplex/submissions/models.py`:

```python
# Add this import at the top of purplex/submissions/models.py
# (after 'from django.db import models')

# Add this field to the Submission model class:
class Submission(models.Model):
    # ... existing fields ...

    # LTI Integration (add after course field)
    lti_launch = models.ForeignKey(
        'lti.LTILaunch',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='submissions',
        help_text="LTI launch context if submitted via LMS"
    )
```

Then create and run the migration:

```bash
python manage.py makemigrations submissions --name add_lti_launch_field
python manage.py migrate
```

### URL Configuration

**File: `purplex/lti/urls.py`**

```python
"""
LTI URL Configuration

All LTI endpoints are served under /lti/ prefix.
"""

from django.urls import path

from .views import (
    DeepLinkView,
    JWKSView,
    LTILaunchView,
    LTIProblemView,
    LTISubmitView,
    OIDCLoginView,
)

urlpatterns = [
    # OIDC Login Initiation
    # Canvas sends users here first
    path('login/', OIDCLoginView.as_view(), name='lti_login'),

    # Launch Callback
    # Canvas redirects here after authentication with signed JWT
    path('launch/', LTILaunchView.as_view(), name='lti_launch'),

    # JWKS Endpoint
    # Canvas fetches our public keys from here
    path('jwks/', JWKSView.as_view(), name='lti_jwks'),

    # Problem View (after successful launch)
    path(
        'problem/<str:launch_id>/',
        LTIProblemView.as_view(),
        name='lti_problem'
    ),

    # Submission Endpoint
    path(
        'problem/<str:launch_id>/submit/',
        LTISubmitView.as_view(),
        name='lti_submit'
    ),

    # Deep Linking (for assignment selection)
    path(
        'deep-link/<str:launch_id>/',
        DeepLinkView.as_view(),
        name='lti_deep_link'
    ),
]
```

**Add to `purplex/urls.py`:**

```python
from django.urls import include, path

urlpatterns = [
    # ... existing patterns ...
    path('lti/', include('purplex.lti.urls')),
]
```

### Django Templates

**File: `purplex/lti/templates/lti/error.html`**

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LTI Error - Purplex</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: system-ui, -apple-system, sans-serif;
            background: #242424;
            color: #ffffff;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 2rem;
        }
        .error-container {
            max-width: 500px;
            text-align: center;
            background: #1e1e1e;
            padding: 2rem;
            border-radius: 12px;
            border: 1px solid #444;
        }
        .error-icon {
            font-size: 3rem;
            margin-bottom: 1rem;
        }
        .error-title {
            color: #dc3545;
            font-size: 1.5rem;
            margin-bottom: 0.5rem;
        }
        .error-details {
            color: #999;
            margin-bottom: 1rem;
            font-size: 0.9rem;
        }
        .error-help {
            color: #ccc;
            font-size: 0.875rem;
        }
    </style>
</head>
<body>
    <div class="error-container">
        <div class="error-icon">&#9888;</div>
        <h1 class="error-title">{{ error }}</h1>
        {% if details %}
        <p class="error-details">{{ details }}</p>
        {% endif %}
        <p class="error-help">Please return to Canvas and try again. If the problem persists, contact your instructor.</p>
    </div>
</body>
</html>
```

**File: `purplex/lti/templates/lti/problem.html`**

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ problem.title }} - Purplex</title>
    <link rel="stylesheet" href="/static/lti/styles.css">
</head>
<body>
    <div id="app" data-launch='{{ launch_data_json|safe }}'></div>

    <!-- Load Vue app bundle -->
    <script type="module" src="/static/lti/lti-bundle.js"></script>

    <!-- Fallback for non-SPA rendering -->
    <noscript>
        <div class="problem-container">
            <h1>{{ problem.title }}</h1>
            <p>JavaScript is required to use Purplex.</p>
        </div>
    </noscript>
</body>
</html>
```

**File: `purplex/lti/templates/lti/deep_link.html`**

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Select Problem - Purplex</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: system-ui, -apple-system, sans-serif;
            background: #242424;
            color: #ffffff;
            min-height: 100vh;
            padding: 2rem;
        }
        .container { max-width: 800px; margin: 0 auto; }
        h1 { margin-bottom: 0.5rem; }
        .subtitle { color: #999; margin-bottom: 2rem; }
        .problem-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 1rem;
        }
        .problem-card {
            background: #1e1e1e;
            border: 1px solid #444;
            border-radius: 8px;
            padding: 1rem;
            cursor: pointer;
            transition: border-color 0.2s, background 0.2s;
        }
        .problem-card:hover {
            border-color: #800080;
            background: #2a2a2a;
        }
        .problem-card.selected {
            border-color: #800080;
            background: #3a1a3a;
        }
        .problem-title { font-weight: 600; margin-bottom: 0.25rem; }
        .problem-type {
            font-size: 0.75rem;
            color: #999;
            text-transform: uppercase;
        }
        .difficulty {
            display: inline-block;
            font-size: 0.7rem;
            padding: 0.2rem 0.5rem;
            border-radius: 4px;
            margin-top: 0.5rem;
        }
        .difficulty.easy { background: #2d4d3a; color: #a3e9c1; }
        .difficulty.intermediate { background: #4d4c2d; color: #e9e4a3; }
        .difficulty.advanced { background: #4d2d2d; color: #e9a3a3; }
        .actions {
            margin-top: 2rem;
            display: flex;
            gap: 1rem;
            justify-content: flex-end;
        }
        .btn {
            padding: 0.75rem 1.5rem;
            border: none;
            border-radius: 6px;
            font-size: 1rem;
            cursor: pointer;
            transition: opacity 0.2s;
        }
        .btn:disabled { opacity: 0.5; cursor: not-allowed; }
        .btn-primary { background: #800080; color: white; }
        .btn-secondary { background: #444; color: white; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Select a Problem</h1>
        <p class="subtitle">Choose a problem for this assignment in {{ launch.context_title }}</p>

        <form method="post" id="problem-form">
            {% csrf_token %}
            <input type="hidden" name="problem_slug" id="problem_slug" value="">

            <div class="problem-grid">
                {% for problem in problems %}
                <div class="problem-card" data-slug="{{ problem.slug }}" onclick="selectProblem(this)">
                    <div class="problem-title">{{ problem.title }}</div>
                    <div class="problem-type">{{ problem.problem_type }}</div>
                    {% if problem.difficulty %}
                    <span class="difficulty {{ problem.difficulty }}">{{ problem.difficulty }}</span>
                    {% endif %}
                </div>
                {% empty %}
                <p>No problems available.</p>
                {% endfor %}
            </div>

            <div class="actions">
                <button type="button" class="btn btn-secondary" onclick="window.history.back()">Cancel</button>
                <button type="submit" class="btn btn-primary" id="submit-btn" disabled>Select Problem</button>
            </div>
        </form>
    </div>

    <script>
        function selectProblem(card) {
            document.querySelectorAll('.problem-card').forEach(c => c.classList.remove('selected'));
            card.classList.add('selected');
            document.getElementById('problem_slug').value = card.dataset.slug;
            document.getElementById('submit-btn').disabled = false;
        }
    </script>
</body>
</html>
```

---

## Frontend Implementation

### Vue Components

**File: `purplex/client/src/features/lti/LTIProblem.vue`**

```vue
<template>
  <div
    ref="containerRef"
    class="lti-container"
    :class="{ 'is-loading': isLoading, 'has-error': hasError }"
  >
    <!-- Loading State -->
    <div v-if="isLoading" class="lti-loading">
      <div class="loading-spinner" />
      <p>Loading problem...</p>
    </div>

    <!-- Error State -->
    <div v-else-if="hasError" class="lti-error">
      <p class="error-title">{{ errorTitle }}</p>
      <p class="error-message">{{ errorMessage }}</p>
      <p class="error-help">Please return to Canvas and try again.</p>
    </div>

    <!-- Problem Content -->
    <div v-else class="lti-content">
      <!-- Header with context info -->
      <header class="lti-header">
        <div class="header-left">
          <h1 class="problem-title">{{ problem?.title }}</h1>
          <span v-if="contextTitle" class="context-badge">
            {{ contextTitle }}
          </span>
        </div>
        <div class="header-right">
          <span v-if="userName" class="user-name">{{ userName }}</span>
          <span
            v-if="problem?.difficulty"
            class="difficulty-badge"
            :class="problem.difficulty"
          >
            {{ problem.difficulty }}
          </span>
        </div>
      </header>

      <!-- Main Problem Layout -->
      <div class="lti-layout">
        <!-- Left: Problem Display -->
        <section class="problem-section">
          <!-- Code Editor (read-only reference) -->
          <div
            v-if="showReferenceCode"
            class="code-display"
          >
            <div class="section-label">Reference Code</div>
            <Editor
              :value="problem?.reference_solution || ''"
              lang="python"
              mode="python"
              height="350px"
              width="100%"
              :read-only="true"
              :show-gutter="true"
              theme="tomorrow_night"
            />
          </div>

          <!-- Problem Image (for prompt type) -->
          <div
            v-else-if="problem?.display_config?.show_image"
            class="problem-image-container"
          >
            <img
              :src="problem.display_config?.image_url"
              :alt="problem.display_config?.image_alt_text || 'Problem image'"
              class="problem-image"
            />
          </div>

          <!-- Description -->
          <div
            v-if="problem?.description"
            class="problem-description"
            v-html="renderedDescription"
          />
        </section>

        <!-- Right: Input & Feedback -->
        <section class="interaction-section">
          <!-- Input -->
          <div class="input-container">
            <InputSelector
              v-model="userInput"
              :activity-type="problem?.problem_type || 'eipl'"
              :problem="problem"
              :disabled="isSubmitting"
              theme="dark"
              :draft-saved="false"
              @submit="handleSubmit"
            />
          </div>

          <!-- Feedback -->
          <div class="feedback-container">
            <FeedbackSelector
              :activity-type="problem?.problem_type || 'eipl'"
              :progress="feedback.promptCorrectness"
              :notches="6"
              :code-results="feedback.codeResults"
              :test-results="feedback.testResults"
              :comprehension-results="feedback.comprehensionResults"
              :user-prompt="feedback.userPrompt"
              :segmentation="feedback.segmentationData"
              :mcq-result="feedback.mcqResult"
              :reference-code="problem?.reference_solution || ''"
              :segmentation-enabled="problem?.feedback_config?.show_segmentation"
              :is-loading="isSubmitting"
              :is-navigating="false"
              :submission-history="[]"
              title="Results"
            />

            <!-- Grade Status -->
            <div v-if="gradeSubmitted" class="grade-status">
              <span class="grade-icon">✓</span>
              Grade sent to Canvas
            </div>
          </div>
        </section>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * LTIProblem - Problem view for LTI-launched sessions
 *
 * This component renders a single problem in an LTI context.
 * User identity is already verified via LTI launch.
 * Grades are automatically submitted to Canvas on completion.
 */
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { marked } from 'marked'

// Components
import Editor from '@/features/editor/Editor.vue'
import InputSelector from '@/components/activities/InputSelector.vue'
import FeedbackSelector from '@/components/activities/FeedbackSelector.vue'

// Composables
import { useFeedbackState } from '@/composables/useFeedbackState'
import { useLTIContext, type LTIContextData } from '@/composables/useLTIContext'

// Types
import type { ActivityProblem } from '@/components/activities/types'

// ===== ROUTE & PROPS =====
const route = useRoute()
const launchId = computed(() => route.params.launchId as string)

// LTI context data injected by Django template or fetched from API
const props = defineProps<{
  initialData?: LTIContextData
}>()

// ===== STATE =====
const containerRef = ref<HTMLElement | null>(null)
const problem = ref<ActivityProblem | null>(null)
const userInput = ref('')
const isLoading = ref(true)
const isSubmitting = ref(false)
const hasError = ref(false)
const errorTitle = ref('')
const errorMessage = ref('')
const gradeSubmitted = ref(false)

// Context from LTI launch
const userName = ref('')
const contextTitle = ref('')
const canSubmitGrade = ref(false)

// ===== COMPOSABLES =====
const { feedback, clear: clearFeedback, set: setFeedback } = useFeedbackState()
const { notifyResize } = useLTIContext()

// ===== COMPUTED =====
const renderedDescription = computed(() => {
  if (!problem.value?.description) return ''
  return marked(problem.value.description, { breaks: true })
})

const showReferenceCode = computed(() => {
  return problem.value?.display_config?.show_reference_code !== false &&
         problem.value?.reference_solution
})

// ===== METHODS =====
async function loadProblem(): Promise<void> {
  isLoading.value = true
  hasError.value = false

  try {
    // Try to get data from props (server-rendered) or fetch from API
    if (props.initialData) {
      applyLaunchData(props.initialData)
    } else {
      const response = await fetch(`/lti/api/launch/${launchId.value}/`)
      if (!response.ok) {
        throw new Error(await response.text())
      }
      const data = await response.json()
      applyLaunchData(data)
    }

    await nextTick()
    notifyResize()

  } catch (error) {
    hasError.value = true
    errorTitle.value = 'Failed to Load Problem'
    errorMessage.value = error instanceof Error ? error.message : 'Unknown error'
  } finally {
    isLoading.value = false
  }
}

function applyLaunchData(data: LTIContextData): void {
  problem.value = data.problem
  userName.value = data.user_name || ''
  contextTitle.value = data.context_title || ''
  canSubmitGrade.value = data.can_submit_grade || false
}

async function handleSubmit(): Promise<void> {
  if (!problem.value || isSubmitting.value) return

  isSubmitting.value = true
  clearFeedback()
  gradeSubmitted.value = false

  try {
    const response = await fetch(`/lti/problem/${launchId.value}/submit/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include',
      body: JSON.stringify({
        raw_input: userInput.value.trim(),
      }),
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.error || 'Submission failed')
    }

    const result = await response.json()
    handleResult(result)

  } catch (error) {
    console.error('Submission error:', error)
    // Show error in feedback
    setFeedback({
      promptCorrectness: 0,
      userPrompt: userInput.value,
    })
  } finally {
    isSubmitting.value = false
    notifyResize()
  }
}

function handleResult(result: any): void {
  // Set feedback based on problem type
  if (result.problem_type === 'mcq') {
    setFeedback({
      mcqResult: {
        is_correct: result.is_correct,
        score: result.score,
        submission_id: result.submission_id,
        selected_option: result.selected_option,
        correct_option: result.correct_option,
        completion_status: result.completion_status,
      },
      promptCorrectness: result.score,
      userPrompt: userInput.value,
    })
  } else {
    setFeedback({
      codeResults: result.variations || [],
      testResults: result.test_results || [],
      promptCorrectness: result.score,
      userPrompt: userInput.value,
      segmentationData: result.segmentation || null,
      comprehensionResults: result.comprehension_level || null,
    })
  }

  // Check if grade was submitted
  if (result.grade_submitted) {
    gradeSubmitted.value = true
  }
}

// ===== RESIZE HANDLING =====
let resizeObserver: ResizeObserver | null = null

function setupResizeObserver(): void {
  if (containerRef.value) {
    resizeObserver = new ResizeObserver(() => {
      notifyResize()
    })
    resizeObserver.observe(containerRef.value)
  }
}

// ===== LIFECYCLE =====
onMounted(() => {
  loadProblem()
  setupResizeObserver()
})

onUnmounted(() => {
  resizeObserver?.disconnect()
})
</script>

<style scoped>
/* LTI-specific styles - optimized for iframe embedding */
.lti-container {
  min-height: 100vh;
  background: var(--color-bg-main, #242424);
  color: var(--color-text-primary, #ffffff);
  font-family: system-ui, -apple-system, sans-serif;
  padding: 1rem;
}

/* Loading */
.lti-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 400px;
  color: var(--color-text-muted, #999);
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--color-bg-input, #333);
  border-top-color: var(--color-primary, #800080);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin-bottom: 1rem;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Error */
.lti-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 300px;
  text-align: center;
  padding: 2rem;
}

.error-title {
  color: var(--color-error, #dc3545);
  font-size: 1.25rem;
  margin-bottom: 0.5rem;
}

.error-message {
  color: var(--color-text-muted, #999);
  margin-bottom: 0.5rem;
}

.error-help {
  color: var(--color-text-secondary, #ccc);
  font-size: 0.875rem;
}

/* Header */
.lti-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
  margin-bottom: 1rem;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid var(--color-bg-border, #444);
}

.header-left {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.problem-title {
  font-size: 1.25rem;
  font-weight: 600;
  margin: 0;
}

.context-badge {
  font-size: 0.75rem;
  color: var(--color-text-muted, #999);
}

.user-name {
  font-size: 0.875rem;
  color: var(--color-text-secondary, #ccc);
}

.difficulty-badge {
  font-size: 0.75rem;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-weight: 600;
  text-transform: capitalize;
}

.difficulty-badge.easy { background: #2d4d3a; color: #a3e9c1; }
.difficulty-badge.beginner { background: #2d3a4d; color: #a3c9e9; }
.difficulty-badge.intermediate { background: #4d4c2d; color: #e9e4a3; }
.difficulty-badge.advanced { background: #4d2d2d; color: #e9a3a3; }

/* Layout */
.lti-layout {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

@media (max-width: 900px) {
  .lti-layout {
    grid-template-columns: 1fr;
  }
}

/* Sections */
.problem-section,
.interaction-section {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.section-label {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-text-secondary, #e0e0e0);
  margin-bottom: 0.5rem;
}

/* Code Display */
.code-display {
  background: var(--color-bg-panel, #1e1e1e);
  border-radius: 8px;
  overflow: hidden;
}

.code-display .section-label {
  padding: 0.75rem 1rem;
  background: var(--color-bg-hover, #2a2a2a);
  margin: 0;
  border-bottom: 1px solid var(--color-bg-border, #444);
}

/* Problem Image */
.problem-image-container {
  background: var(--color-bg-panel, #1e1e1e);
  border-radius: 8px;
  padding: 1rem;
  text-align: center;
}

.problem-image {
  max-width: 100%;
  height: auto;
  border-radius: 4px;
}

/* Description */
.problem-description {
  background: var(--color-bg-panel, #1e1e1e);
  border-radius: 8px;
  padding: 1rem;
  line-height: 1.6;
}

/* Input/Feedback containers */
.input-container,
.feedback-container {
  background: var(--color-bg-panel, #1e1e1e);
  border-radius: 8px;
  overflow: hidden;
}

/* Grade Status */
.grade-status {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  background: var(--color-bg-success, #2d4d3a);
  color: var(--color-text-success, #a3e9c1);
  font-size: 0.875rem;
  border-radius: 0 0 8px 8px;
}

.grade-icon {
  font-weight: bold;
}
</style>
```

### Composables

**File: `purplex/client/src/composables/useLTIContext.ts`**

```typescript
/**
 * useLTIContext - Composable for LTI-specific functionality
 *
 * Provides:
 * - Frame resize notifications (lti.frameResize postMessage)
 * - LTI context data access
 * - Session management
 */

import { ref, onMounted, onUnmounted } from 'vue'

export interface LTIContextData {
  launch_id: string
  problem_slug: string
  problem_title: string
  problem: any // ActivityProblem
  user_name: string
  context_title: string
  can_submit_grade: boolean
}

export interface UseLTIContextReturn {
  /** Notify parent frame of size change */
  notifyResize: () => void
  /** Current LTI context data */
  context: LTIContextData | null
  /** Whether we're in an LTI iframe */
  isLTIContext: boolean
}

export function useLTIContext(): UseLTIContextReturn {
  const context = ref<LTIContextData | null>(null)

  // Check if we're in an iframe (LTI context)
  const isLTIContext = window.self !== window.top

  /**
   * Notify parent frame of document size changes.
   * Canvas uses this to resize the iframe.
   */
  function notifyResize(): void {
    if (!isLTIContext) return

    const height = document.documentElement.scrollHeight
    const width = document.documentElement.scrollWidth

    window.parent.postMessage({
      subject: 'lti.frameResize',
      height,
      width,
    }, '*')
  }

  // Setup resize observer for automatic notifications
  let resizeObserver: ResizeObserver | null = null

  onMounted(() => {
    if (!isLTIContext) return

    resizeObserver = new ResizeObserver(() => {
      notifyResize()
    })
    resizeObserver.observe(document.body)

    // Initial resize notification
    notifyResize()
  })

  onUnmounted(() => {
    resizeObserver?.disconnect()
  })

  return {
    notifyResize,
    context: context.value,
    isLTIContext,
  }
}
```

### Router Configuration

**File: `purplex/client/src/router.ts`** (add to routes)

```typescript
// Add LTI route
{
  path: "/lti/problem/:launchId",
  name: "LTIProblem",
  component: () => import("./features/lti/LTIProblem.vue"),
  meta: {
    lti: true,
    requiresAuth: false  // Auth handled by LTI launch
  }
}

// Update beforeEach guard to skip LTI routes
router.beforeEach(async (to, _from, next) => {
  // Skip auth checks for LTI routes
  if (to.meta?.lti) {
    next()
    return
  }

  // ... rest of existing guard logic
})
```

---

## Settings Configuration

**File: `purplex/settings/base.py`** (additions)

```python
# Add 'lti' to INSTALLED_APPS
INSTALLED_APPS = [
    # ... existing apps ...
    'purplex.lti',
]

# Add LTI session middleware
MIDDLEWARE = [
    # ... existing middleware ...
    'purplex.lti.cache_session.SessionCookieMiddleware',
]

# LTI Settings
LTI_CONFIG = {
    # Default session duration
    'LAUNCH_SESSION_HOURS': 4,

    # Grade passback settings
    'AUTO_SUBMIT_GRADES': True,
    'GRADE_DECIMAL_PLACES': 2,

    # Security
    'REQUIRE_HTTPS': not DEBUG,
}

# Cache settings (ensure Redis is configured)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': env('REDIS_URL', default='redis://localhost:6379/1'),
    }
}

# Cookie settings for LTI iframes
SESSION_COOKIE_SAMESITE = 'Lax'  # Default Django sessions
# LTI uses its own cookies with SameSite=None
```

---

## Canvas Admin Setup

### Step 1: Create Developer Key

1. Log into Canvas as admin
2. Go to **Admin** → **Developer Keys**
3. Click **+ Developer Key** → **LTI Key**
4. Configure:

| Field | Value |
|-------|-------|
| Key Name | Purplex |
| Redirect URIs | `https://your-domain.com/lti/launch/` |
| Target Link URI | `https://your-domain.com/lti/launch/` |
| OpenID Connect Initiation URL | `https://your-domain.com/lti/login/` |
| JWK Method | Public JWK URL |
| Public JWK URL | `https://your-domain.com/lti/jwks/` |

5. Enable **LTI Advantage Services**:
   - ✅ Can create and view assignment data
   - ✅ Can view submission data
   - ✅ Can create and update submission results

6. Set **Placements**:
   - ✅ Assignment Selection (for deep linking)

7. Add **Custom Fields**:
   ```
   problem_slug=$Canvas.resourceLink.title
   ```

8. Save and note the **Client ID**

### Step 2: Configure Purplex Platform

Create an `LTIPlatform` record in Django admin or via management command:

```python
from purplex.lti.models import LTIPlatform, LTIDeployment

# Generate RSA keys
private_key, public_key = LTIPlatform.generate_rsa_keys()

# Create platform
platform = LTIPlatform.objects.create(
    name='University Canvas',
    issuer='https://canvas.university.edu',
    client_id='YOUR_CLIENT_ID_FROM_CANVAS',
    auth_login_url='https://canvas.university.edu/api/lti/authorize_redirect',
    auth_token_url='https://canvas.university.edu/login/oauth2/token',
    key_set_url='https://canvas.university.edu/api/lti/security/jwks',
    private_key=private_key,
    public_key=public_key,
    is_active=True,
)

# Create deployment
LTIDeployment.objects.create(
    platform=platform,
    deployment_id='YOUR_DEPLOYMENT_ID',  # From Canvas
)
```

### Step 3: Install Tool in Course

1. Go to course **Settings** → **Apps**
2. Click **+ App**
3. Configuration Type: **By Client ID**
4. Enter the Client ID
5. Click **Submit** → **Install**

---

## Instructor Workflow

### Creating an LTI Assignment

1. **In Canvas:**
   - Create new Assignment
   - Set **Submission Type** to **External Tool**
   - Click **Find** and select **Purplex**

2. **Purplex Deep Link Interface:**
   - List of available problems appears
   - Select the desired problem
   - Click **Select**

3. **Back in Canvas:**
   - Assignment is configured with the problem
   - Set points, due date, etc.
   - Save assignment

### Student Experience

1. Student opens assignment in Canvas
2. LTI launch authenticates automatically
3. Problem appears in iframe
4. Student submits solution
5. Grade automatically appears in Canvas gradebook

---

## Security Considerations

### Authentication
- All launches validated via JWT signature verification
- Canvas signs JWTs with its private key
- Purplex verifies using Canvas's public JWKS

### Session Security
- Cache-based sessions avoid iframe cookie issues
- `SameSite=None; Secure` cookies required
- Sessions expire after 4 hours

### Transport Security
- HTTPS required in production
- All LTI endpoints use TLS

### Data Privacy
- Only necessary user data is stored
- Email/name can be omitted if Canvas doesn't send
- No passwords stored (Canvas handles auth)

### Grade Integrity
- Grades can only be submitted for valid launches
- AGS tokens are scoped per launch
- Grade updates require re-authentication

---

## Testing Guide

### Local Testing with ngrok

```bash
# Start ngrok tunnel
ngrok http 8000

# Use ngrok URL in Canvas Developer Key configuration
# https://xxxx.ngrok.io/lti/login/
# https://xxxx.ngrok.io/lti/launch/
# https://xxxx.ngrok.io/lti/jwks/
```

### Test Checklist

1. **OIDC Login Flow**
   - Canvas redirects to `/lti/login/`
   - Purplex redirects to Canvas auth
   - Canvas redirects back to `/lti/launch/`

2. **Launch Validation**
   - JWT signature verified
   - User created/updated in LTIUser
   - Launch record created

3. **Problem View**
   - Problem renders correctly in iframe
   - User name displayed
   - Input/feedback components work

4. **Submission**
   - Submit button works
   - Results displayed
   - No JavaScript errors

5. **Grade Passback**
   - Grade appears in Canvas gradebook
   - Correct score value
   - Comment included

6. **Deep Linking**
   - Instructor can select problems
   - Assignment configured correctly
   - Students see correct problem

---

## Troubleshooting

### Common Issues

**"Invalid signature" error**
- Check JWKS endpoint returns correct keys: `curl https://your-domain.com/lti/jwks/`
- Verify `issuer` matches Canvas URL exactly (no trailing slash differences)
- Ensure private/public keys match - regenerate if unsure:
  ```python
  from purplex.lti.models import LTIPlatform
  priv, pub = LTIPlatform.generate_rsa_keys()
  platform = LTIPlatform.objects.get(issuer='https://canvas.university.edu')
  platform.private_key = priv
  platform.public_key = pub
  platform.save()
  ```
- Check Canvas Developer Key is in "ON" state (not "OFF" or "Pending")

**Session lost after redirect**
- Check `SameSite=None; Secure` on cookies - inspect in browser DevTools > Application > Cookies
- Verify cache backend is working: `python manage.py shell -c "from django.core.cache import cache; cache.set('test', 1); print(cache.get('test'))"`
- Check Redis connection: `redis-cli ping`
- Ensure HTTPS is properly configured (required for `SameSite=None`)

**Grade not appearing**
- Verify AGS scopes granted in Canvas Developer Key:
  - `https://purl.imsglobal.org/spec/lti-ags/scope/score`
  - `https://purl.imsglobal.org/spec/lti-ags/scope/lineitem`
- Check `ags_lineitem` is set on launch: query `LTILaunch.objects.filter(ags_lineitem='').count()`
- Look for errors in grade submission logs (see Logging section below)
- Verify the assignment in Canvas has a grade column (not "Complete/Incomplete")

**iframe blocked**
- Check X-Frame-Options header is NOT set for `/lti/` routes:
  ```python
  # In purplex/lti/middleware.py or views
  response['X-Frame-Options'] = 'ALLOWALL'  # Or remove the header entirely
  ```
- Verify CSP allows Canvas origin - add to settings:
  ```python
  CSP_FRAME_ANCESTORS = ["'self'", "https://*.instructure.com", "https://canvas.university.edu"]
  ```
- Canvas may need to whitelist your domain in Admin > Settings > Security

**"Platform not found" error**
- Check the `issuer` URL in the database matches exactly what Canvas sends
- Run: `LTIPlatform.objects.values_list('issuer', flat=True)` to see registered issuers
- Verify `is_active=True` on the platform

**Deep linking not returning to Canvas**
- Ensure the deep link response form auto-submits (JavaScript enabled)
- Check the return URL is set correctly in Canvas Developer Key
- Verify instructor has proper permissions in the Canvas course

### Debugging Commands

```bash
# Check LTI platform configuration
python manage.py shell -c "
from purplex.lti.models import LTIPlatform
for p in LTIPlatform.objects.all():
    print(f'{p.name}: {p.issuer} (active={p.is_active})')
"

# Check recent launches
python manage.py shell -c "
from purplex.lti.models import LTILaunch
for l in LTILaunch.objects.order_by('-created_at')[:5]:
    print(f'{l.launch_id[:8]}... - {l.lti_user.name} - {l.problem.slug} - expired={l.is_expired}')
"

# Test Redis cache
python manage.py shell -c "
from django.core.cache import cache
cache.set('lti:test', 'working', 60)
print(f'Cache test: {cache.get(\"lti:test\")}')
"

# Verify JWKS endpoint
curl -s https://your-domain.com/lti/jwks/ | python -m json.tool
```

### Logging

Enable debug logging in `purplex/settings/base.py`:

```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{asctime} {levelname} {name} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': 'logs/lti.log',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'purplex.lti': {
            'level': 'DEBUG',
            'handlers': ['console', 'file'],
            'propagate': False,
        },
        'pylti1p3': {
            'level': 'DEBUG',
            'handlers': ['console'],
            'propagate': False,
        },
    },
}
```

### Log Locations

| Log Type | Location |
|----------|----------|
| LTI App Logs | `logs/lti.log` (if file handler configured) |
| Django Console | stdout when running `manage.py runserver` |
| Celery Worker | Celery worker console output |
| Nginx Access | `/var/log/nginx/access.log` |
| Nginx Error | `/var/log/nginx/error.log` |

---

## References

### Library Documentation
- [PyLTI1p3 Documentation](https://pypi.org/project/PyLTI1p3/) - Python library for LTI 1.3
- [PyLTI1p3 GitHub Wiki](https://github.com/dmitry-viskov/pylti1.3/wiki) - Detailed configuration guides
- [Canvas LTI 1.3 Configuration](https://github.com/dmitry-viskov/pylti1.3/wiki/Configure-Canvas-as-LTI-1.3-Platform) - Canvas-specific setup

### IMS Global Specifications
- [LTI 1.3 Core Specification](https://www.imsglobal.org/spec/lti/v1p3/) - Core LTI standard
- [LTI Assignment and Grades Service (AGS)](https://www.imsglobal.org/spec/lti-ags/v2p0) - Grade passback
- [LTI Deep Linking](https://www.imsglobal.org/spec/lti-dl/v2p0) - Content selection
- [LTI Names and Roles Provisioning (NRPS)](https://www.imsglobal.org/spec/lti-nrps/v2p0) - Roster access

### Canvas Documentation
- [Canvas LTI Developer Keys](https://community.canvaslms.com/t5/Admin-Guide/How-do-I-configure-an-LTI-key-for-an-account/ta-p/140) - Canvas admin guide
- [Canvas API Reference](https://canvas.instructure.com/doc/api/) - Canvas REST API
- [Canvas Free-for-Teacher](https://www.instructure.com/canvas/try-canvas) - Free Canvas instance for testing

### Related Purplex Documentation
- [CLAUDE.md](/CLAUDE.md) - Project overview and development commands
- [Architecture Guide](/docs/architecture/ARCHITECTURE.md) - System architecture
- [Testing Guide](/docs/TESTING.md) - Testing strategies
