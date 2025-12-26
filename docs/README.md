# Purplex Documentation

Complete documentation for the Purplex educational coding platform.

## Reading Order for New Developers

1. [Project README](../README.md) - Setup and quick start
2. [Architecture Overview](./architecture/ARCHITECTURE.md) - System design
3. [Development Workflow](./development/DEVELOPMENT.md) - Daily workflow
4. [Coding Standards](./development/STANDARDS.md) - Required patterns

## Documentation Index

### Architecture

| Document | Description |
|----------|-------------|
| [ARCHITECTURE.md](./architecture/ARCHITECTURE.md) | System overview, data flows, component structure |
| [POLYMORPHIC_ARCHITECTURE.md](./architecture/POLYMORPHIC_ARCHITECTURE.md) | Polymorphic model design for problem types |
| [PROBLEM_TYPES.md](./architecture/PROBLEM_TYPES.md) | Catalog of all 7 activity types |

### Development

| Document | Description |
|----------|-------------|
| [DEVELOPMENT.md](./development/DEVELOPMENT.md) | Development environment setup and workflows |
| [STANDARDS.md](./development/STANDARDS.md) | Coding standards and conventions |
| [PATTERNS.md](./development/PATTERNS.md) | Implementation patterns with code examples |
| [NEW_PROBLEM_TYPE_GUIDE.md](./development/NEW_PROBLEM_TYPE_GUIDE.md) | Step-by-step guide to adding new problem types |
| [ADMIN_PANEL_GUIDE.md](./development/ADMIN_PANEL_GUIDE.md) | Admin interface development |
| [FIELD_NAMING_GUIDE.md](./development/FIELD_NAMING_GUIDE.md) | Database field naming conventions |
| [TESTING_QUICK_REFERENCE.md](./development/TESTING_QUICK_REFERENCE.md) | Testing commands cheatsheet |

### Deployment

| Document | Description |
|----------|-------------|
| [DOCKER_DEPLOYMENT.md](./deployment/DOCKER_DEPLOYMENT.md) | Docker Compose deployment guide |
| [DEPLOYMENT_CHECKLIST.md](./deployment/DEPLOYMENT_CHECKLIST.md) | Pre-deployment verification checklist |
| [CONFIGURATION.md](./deployment/CONFIGURATION.md) | Environment variables reference |
| [CONFIGURATION_MIGRATION_GUIDE.md](./deployment/CONFIGURATION_MIGRATION_GUIDE.md) | Migrating between environments |

### Security

| Document | Description |
|----------|-------------|
| [SECURITY.md](./security/SECURITY.md) | Security policies, authentication, code execution |
| [CONFIGURATION_SECURITY_CHECKLIST.md](./security/CONFIGURATION_SECURITY_CHECKLIST.md) | Security configuration checklist |

### Frontend

| Document | Description |
|----------|-------------|
| [FRONTEND_COMPONENT_STRUCTURE.md](./frontend/FRONTEND_COMPONENT_STRUCTURE.md) | Vue component architecture for activities |
| [HANDLER_IMPLEMENTATION_DETAILS.md](./frontend/HANDLER_IMPLEMENTATION_DETAILS.md) | Handler pattern implementation details |

### Integrations

| Document | Description |
|----------|-------------|
| [LTI_CANVAS_INTEGRATION.md](./integrations/LTI_CANVAS_INTEGRATION.md) | Canvas LMS integration (LTI 1.3) |

### Reference

| Document | Description |
|----------|-------------|
| [TESTING.md](./reference/TESTING.md) | Testing strategy and guidelines |
| [TECH_DEBT.md](./reference/TECH_DEBT.md) | Technical debt registry |

### Plans & Roadmap

| Document | Description |
|----------|-------------|
| [TODO_MULTILINGUAL.md](./plans/TODO_MULTILINGUAL.md) | i18n implementation checklist |
| [EIPL_FEEDBACK_REDESIGN.md](./plans/EIPL_FEEDBACK_REDESIGN.md) | Feedback panel redesign spec |
| [ACTIVITY_EVENT_LOGGING_PLAN.md](./plans/ACTIVITY_EVENT_LOGGING_PLAN.md) | Activity logging design |

## Quick Links

- [Project README](../README.md) - Setup instructions
- [Environment Example](../.env.example) - Configuration template
- [Makefile](../Makefile) - Available make commands

## External Resources

- [Django Documentation](https://docs.djangoproject.com/)
- [Vue.js Documentation](https://vuejs.org/guide/)
- [Celery Documentation](https://docs.celeryq.dev/)
- [Docker Documentation](https://docs.docker.com/)
- [django-polymorphic Documentation](https://django-polymorphic.readthedocs.io/)
