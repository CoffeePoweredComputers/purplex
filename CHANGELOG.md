# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-02-21

### Added

- AI-powered problem generation using OpenAI GPT-4 and Meta Llama
- Docker-based sandboxed code execution with resource limits and network isolation
- EiPL (Explain in Plain Language) submission system for natural language code explanations
- Multi-modal hint system: Variable Fade, Subgoal Highlighting, Suggested Trace
- Course and problem set management for instructors
- Real-time submission processing via Celery task queue with SSE status updates
- Comprehensive progress tracking and analytics
- Firebase authentication with Google Sign-In (mock auth for development)
- FERPA-compliant directory information controls
- GDPR/CCPA/DPDPA privacy compliance: consent management, data export, account deletion
- Cookie consent banner (ePrivacy Directive)
- Research data export with anonymization (SHA-256 hashing)
- Audit logging middleware for instructor/admin access
- Age verification and COPPA compliance for users under 13
- Data Principal Nominee management (DPDPA Sec. 8(7))
- Automated data retention cleanup command
- Vue 3 + TypeScript frontend with Ace code editor
- Internationalization support (vue-i18n)
- Docker Compose configuration for development and production
- Comprehensive test suite (pytest + Vitest)
