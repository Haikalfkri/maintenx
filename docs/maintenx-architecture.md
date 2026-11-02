# MaintenX --- Architecture

## 1. Purpose

This document describes the application architecture for the seven-day
MaintenX MVP. MaintenX is a multi-organization equipment maintenance
platform built with Django and Django REST Framework, React, PostgreSQL,
Celery, and Redis.

The architecture prioritizes understandable modularity, secure
organization-level data isolation, and a working end-to-end product. It
deliberately avoids microservices and unnecessary abstraction.

## 2. System context

``` mermaid
flowchart TD
    U[Admin / Manager / Technician] --> FE[React + TypeScript]
    FE -->|HTTPS / JSON REST API| API[Django REST Framework]
    API --> DB[(PostgreSQL)]
    API --> R[(Redis)]
    W[Celery Worker] --> R
    W --> DB
    B[Celery Beat Scheduler] --> R
```

-   React is responsible for presentation, navigation, forms, and
    client-side interaction.
-   Django REST Framework is the authoritative application layer for
    authentication, permissions, validation, business rules, and
    reporting.
-   PostgreSQL stores operational and audit data.
-   Redis acts as the Celery broker.
-   Celery Worker executes background tasks.
-   Celery Beat schedules recurring maintenance checks.

For local development, React and Django may run directly on the host
while PostgreSQL and Redis run in Docker. The final deployment should
run the required services in a controlled container or hosting
environment.

## 3. Architectural style

Use a **modular monolith**.

Each Django app owns a business capability and its models, serializers,
views, services, permissions, URLs, and tests. Apps share one Django
project and one PostgreSQL database.

Do not split the MVP into microservices. Do not introduce a generic
repository layer simply to imitate another framework's architecture.
Django ORM and focused service modules are sufficient.

### Request flow

1.  A user interacts with a React page.
2.  React calls the versioned REST API through a shared API client.
3.  JWT authentication identifies the user.
4.  Permission checks establish whether the role can perform the action.
5.  The queryset is scoped to the user's organization.
6.  Serializer validation checks request data.
7.  A service function applies business rules and performs multi-step
    writes in a transaction where needed.
8.  Django ORM reads or writes PostgreSQL.
9.  DRF returns a documented JSON response.
10. TanStack Query updates or invalidates affected frontend data.

## 4. Backend module responsibilities

``` text
backend/
├── config/
│   ├── settings/
│   ├── urls.py
│   ├── celery.py
│   └── wsgi.py
├── apps/
│   ├── accounts/
│   ├── organizations/
│   ├── equipment/
│   ├── maintenance/
│   ├── work_orders/
│   ├── downtime/
│   ├── analytics/
│   └── audit_logs/
├── common/
└── manage.py
```

  -----------------------------------------------------------------------
  Module                              Responsibility
  ----------------------------------- -----------------------------------
  accounts                            Custom user, login-related profile
                                      and user administration

  organizations                       Organization and tenant
                                      membership/context

  equipment                           Categories, equipment records,
                                      lifecycle and history queries

  maintenance                         Preventive plans, recurrence
                                      calculation and due-plan tasks

  work_orders                         Work-order creation, assignment,
                                      state transitions and history

  downtime                            Breakdown and recovery records,
                                      duration calculations

  analytics                           Organization-scoped KPI and chart
                                      queries

  audit_logs                          Important actor/action/entity event
                                      records

  common                              Shared pagination, exceptions,
                                      permissions and utilities
  -----------------------------------------------------------------------

Each app should remain cohesive. Avoid circular imports; shared
low-level helpers belong in `common`, while business-specific behavior
stays in its owning app.

## 5. Organization isolation and security boundary

The organization is the tenant boundary.

-   Every tenant-owned business model has an explicit `organization`
    foreign key.
-   The authenticated user's organization is derived from trusted
    server-side membership.
-   The API must not trust a client-supplied organization ID to
    authorize access.
-   Every list queryset is filtered by the current organization.
-   Detail and action endpoints must retrieve objects through the scoped
    queryset.
-   Related objects (equipment, maintenance plan, assigned technician,
    work order) must be checked to ensure they belong to the same
    organization.
-   Database uniqueness constraints should include organization where
    appropriate, such as `(organization, equipment_code)`.
-   Automated tests must attempt cross-tenant reads and writes.

For the MVP, each user belongs to one organization. If users later need
membership in multiple organizations, introduce a dedicated membership
model and explicit active-organization selection.

## 6. Business logic placement

Keep API views thin.

-   **Models:** persistent state, simple invariants, database
    relationships.
-   **Serializers:** input/output representation and request validation.
-   **Permissions:** role and object-level authorization.
-   **Services:** business operations such as completing a work order,
    generating due maintenance work orders, recording recovery, and
    calculating KPIs.
-   **Tasks:** Celery entry points that call services.
-   **Selectors/query helpers:** reusable, optimized read queries when
    useful.

Example service responsibilities: -
`MaintenanceSchedulingService.generate_due_work_orders()` -
`WorkOrderService.assign()` - `WorkOrderService.start()` -
`WorkOrderService.complete()` - `DowntimeService.record_recovery()` -
`AnalyticsService.get_overview()`

Use `transaction.atomic()` for operations that update multiple related
records. Avoid putting all business logic in model signals; explicit
service calls are easier to follow and test.

## 7. Background processing

Celery Beat schedules a daily maintenance-due task. The worker: 1. Finds
active plans due on or before the relevant local date. 2. Locks or
otherwise safely claims eligible plan rows where concurrent execution is
possible. 3. Checks whether a work order already exists for that plan
and scheduled due date. 4. Creates at most one preventive work order for
that occurrence. 5. Records the generated occurrence or uses a database
uniqueness constraint to make the operation idempotent. 6. Advances the
next due date according to the agreed recurrence policy after
completion.

The task must be safe to retry. Do not rely only on an in-memory check
to prevent duplicate generation.

## 8. Frontend architecture

``` text
frontend/src/
├── app/
├── components/
│   ├── layout/
│   └── ui/
├── features/
│   ├── auth/
│   ├── dashboard/
│   ├── equipment/
│   ├── maintenance/
│   ├── work-orders/
│   ├── downtime/
│   ├── analytics/
│   └── users/
├── hooks/
├── lib/
│   ├── api-client.ts
│   └── query-client.ts
├── routes/
└── types/
```

-   Feature folders contain pages, feature-specific components, hooks,
    schemas, and API functions.
-   Shared components contain layout and reusable UI primitives.
-   TanStack Query owns server state and cache invalidation.
-   React Hook Form and Zod handle form state and client-side feedback.
-   TypeScript types describe API contracts.
-   The backend remains authoritative for validation and authorization.

## 9. Deployment topology

Production services: - React static frontend served by a suitable static
host or web server. - Django API served by a production WSGI/ASGI
server. - PostgreSQL managed database or secured database container. -
Redis broker. - Celery worker. - Celery Beat scheduler.

Use HTTPS, production environment variables, restricted CORS origins,
secure Django settings, database backups, and centralized logs. Do not
expose PostgreSQL or Redis publicly.

## 10. Key architecture decisions

  -----------------------------------------------------------------------
  Decision                            Reason
  ----------------------------------- -----------------------------------
  Modular monolith                    Fast to build and simple to operate

  Django REST Framework               Mature API, serializer, permission
                                      and authentication ecosystem

  PostgreSQL                          Relational integrity and
                                      aggregation support

  Explicit organization FK            Clear tenant scoping and
                                      constraints

  Service functions                   Testable business workflows

  Celery + Redis                      Reliable scheduled work outside
                                      request/response cycle

  Versioned API                       Stable contract for frontend and
                                      future clients

  OpenAPI docs                        Easier testing, onboarding and
                                      recruiter review
  -----------------------------------------------------------------------

## 11. Architecture quality gates

Before calling the MVP complete: - No endpoint exposes another
organization's records. - State transitions are enforced server-side. -
Scheduled maintenance generation is idempotent. - Multi-record writes
use transactions. - Analytics use database queries and documented
formulas. - Frontend does not contain the only copy of a business
rule. - Production configuration does not use Django's development
server.
