# MaintenX --- Project Specification

**Project type:** Multi-organization equipment maintenance management
platform\
**Delivery target:** 7-day MVP\
**Backend:** Python, Django, Django REST Framework\
**Frontend:** React, TypeScript, Vite\
**Database:** PostgreSQL\
**Background jobs:** Celery + Redis\
**Deployment:** Docker Compose\
**Document status:** MVP implementation blueprint

------------------------------------------------------------------------

## 1. Product overview

### 1.1 Product summary

MaintenX is a web-based maintenance management platform for small and
medium-sized manufacturing businesses, workshops, and industrial
facilities.

It helps maintenance teams:

-   Maintain a centralized register of equipment.
-   Plan and monitor preventive maintenance.
-   Create, assign, and track maintenance work orders.
-   Record equipment breakdowns and downtime.
-   Review maintenance performance through operational metrics.

The MVP is intended to demonstrate a realistic business workflow and
sound software engineering practices. It is not intended to replace a
full enterprise Computerized Maintenance Management System (CMMS).

### 1.2 Problem statement

Maintenance information can be fragmented across spreadsheets, paper
forms, messaging applications, and individual employee knowledge. This
can make it difficult for a business to know:

-   Which equipment is registered and where it is located.
-   Which preventive maintenance tasks are due or overdue.
-   Who is responsible for an active repair.
-   How long equipment was unavailable.
-   Which equipment experiences repeated breakdowns.
-   Whether maintenance activities are completed on time.

MaintenX provides one system of record for these activities.

**Validation note:** These are the problems the product is designed to
address. Before treating them as proven needs for a particular company
or market, validate them through conversations with maintenance managers
and technicians.

### 1.3 Product goals

1.  Provide a reliable equipment register.
2.  Make preventive maintenance schedules visible and actionable.
3.  Give managers a consistent work-order workflow.
4.  Capture breakdown and downtime history.
5.  Calculate transparent maintenance KPIs from recorded data.
6.  Demonstrate secure organization-level data isolation.
7.  Deliver a deployable, documented, tested full-stack application.

### 1.4 Non-goals for the 7-day MVP

The following are explicitly out of scope:

-   IoT sensors and live machine telemetry.
-   Machine-learning or AI failure prediction.
-   Native mobile applications.
-   WebSocket-based live monitoring.
-   Spare-parts inventory and procurement.
-   Complex approval chains.
-   Billing, subscriptions, and payment processing.
-   Integration with ERP, MES, or accounting systems.
-   Offline-first operation.

------------------------------------------------------------------------

## 2. Users, roles, and permissions

Each user belongs to one organization in the MVP. Every business record
must be scoped to that organization.

### 2.1 Roles

  Capability                      Admin   Manager   Technician
  ----------------------------- ------- --------- ------------
  View organization dashboard       Yes       Yes      Limited
  Manage organization users         Yes        No           No
  Create/edit equipment             Yes       Yes           No
  View equipment                    Yes       Yes          Yes
  Create maintenance plans          Yes       Yes           No
  View maintenance plans            Yes       Yes          Yes
  Create work orders                Yes       Yes           No
  Assign technicians                Yes       Yes           No
  View assigned work orders         Yes       Yes          Yes
  Update assigned work orders       Yes       Yes          Yes
  Record downtime                   Yes       Yes          Yes
  View organization analytics       Yes       Yes           No
  View own work history             Yes       Yes          Yes

A technician may only update work orders assigned to them. A manager can
manage operational records but cannot manage organization membership in
the MVP. An admin has full organization-level access.

### 2.2 Authorization principles

-   Authentication identifies the user; authorization determines what
    the user may do.
-   Never trust an `organization_id` supplied by the browser as proof of
    access.
-   Derive the active organization from the authenticated user's
    membership.
-   Scope every queryset by the user's organization.
-   Check object-level permissions for sensitive actions.
-   Test cross-organization access explicitly.
-   Return `404` for inaccessible organization-scoped objects where
    appropriate, to avoid leaking their existence.

------------------------------------------------------------------------

## 3. Functional requirements

### 3.1 Authentication and organization

**Features** - Login using email and password. - Obtain and refresh JWT
access tokens. - Logout by removing client-side tokens; add
refresh-token blacklist support if enabled. - Retrieve the authenticated
user's profile and organization. - Admin can create users within their
organization. - Admin can assign a role to a user. - Admin can
activate/deactivate organization users.

**Acceptance criteria** - Unauthenticated users cannot access protected
API endpoints. - Invalid credentials return a generic authentication
error. - A user cannot access another organization's data by changing an
ID in the URL or request body. - Inactive users cannot authenticate.

### 3.2 Equipment management

**Equipment fields** - Equipment code (unique within organization). -
Name. - Description. - Category. - Manufacturer. - Model number. -
Serial number. - Location. - Purchase date (optional). - Installation
date (optional). - Status: `OPERATIONAL`, `UNDER_MAINTENANCE`,
`OUT_OF_SERVICE`, `RETIRED`. - Created and updated timestamps.

**Features** - Create, view, update, and retire equipment. - Search by
equipment code, name, serial number, or location. - Filter by category,
location, and status. - Paginate results. - View equipment detail and
related maintenance/work-order history.

**Rules** - Equipment code must be unique within an organization. -
Retired equipment cannot receive new maintenance plans or work orders. -
Do not hard-delete equipment with maintenance history; use a retired
status.

### 3.3 Preventive maintenance plans

**Maintenance plan fields** - Equipment. - Title. - Description /
checklist. - Frequency: `DAILY`, `WEEKLY`, `MONTHLY`. - Interval value,
initially fixed at one frequency unit for MVP. - Start date. - Next due
date. - Estimated duration in minutes (optional). - Assigned default
technician (optional). - Active flag. - Created and updated timestamps.

**Features** - Create, view, update, and deactivate plans. - Show
upcoming, due, and overdue plans. - Generate a work order when a plan
becomes due. - Display the next due date and last generated work order.

**Scheduling rules** - A plan is overdue when `next_due_date` is earlier
than the organization's current local date and it has not been
completed/generated according to the agreed workflow. - Celery Beat runs
a scheduled task once daily. - The task must be idempotent: running it
more than once must not create duplicate work orders for the same plan
and due date. - When a plan's maintenance work order is completed,
advance `next_due_date` from the scheduled due date according to the
plan frequency. If the due date has fallen far in the past, calculate
the next future occurrence rather than generating a backlog of duplicate
work orders. - Store timestamps in UTC. Configure the organization's
timezone; use `Asia/Jakarta` as the initial demo organization's
timezone.

**MVP simplification** - Support daily, weekly, and monthly recurrence
only. - No custom cron expressions, multiple calendars, holiday
calendars, or complex recurrence exceptions.

### 3.4 Work order management

**Work order fields** - Work-order number (unique within
organization). - Equipment. - Title. - Description. - Work-order type:
`CORRECTIVE`, `PREVENTIVE`. - Priority: `LOW`, `MEDIUM`, `HIGH`,
`CRITICAL`. - Status: `OPEN`, `ASSIGNED`, `IN_PROGRESS`, `COMPLETED`,
`CANCELLED`. - Assigned technician (optional until assigned). - Due date
(optional). - Reported by. - Maintenance plan (optional). - Started at
(optional). - Completed at (optional). - Completion notes (optional). -
Actual labor minutes (optional). - Created and updated timestamps.

**Workflow**

`OPEN → ASSIGNED → IN_PROGRESS → COMPLETED`

`OPEN / ASSIGNED → CANCELLED`

A manager/admin may perform assignment and cancellation. An assigned
technician may start and complete their work order. A technician cannot
assign work to another technician or alter organization ownership.

**Rules** - A completed or cancelled work order is terminal in the
MVP. - Completing a work order requires completion notes. - Starting a
work order records `started_at`. - Completing a work order records
`completed_at`. - Prevent completion if the equipment belongs to another
organization or is retired. - Status changes must be validated on the
server. - Record important status changes in a work-order history/audit
record. - Use a database transaction when completion updates the work
order, maintenance plan, equipment status, or downtime record together.

### 3.5 Downtime tracking

**Downtime record fields** - Equipment. - Related work order (optional
for a standalone incident). - Breakdown start timestamp. - Recovery/end
timestamp (optional while still down). - Reason/category: `MECHANICAL`,
`ELECTRICAL`, `OPERATOR`, `OTHER`. - Description. - Recorded by. -
Created and updated timestamps.

**Rules** - End time must not be earlier than start time. - An open
downtime record has no end timestamp. - Prevent overlapping open
downtime records for the same equipment. - Downtime duration is
calculated from timestamps; do not accept a client-provided duration as
authoritative. - Completing a related corrective work order should close
its linked downtime record when the user explicitly confirms recovery. -
Equipment may be marked `OUT_OF_SERVICE` while an active downtime record
exists. Returning it to `OPERATIONAL` should require a recovery action
or authorized manager action.

### 3.6 Dashboard and analytics

The dashboard must use real database queries, not hardcoded values.

**MVP summary cards** - Total active equipment. - Open work orders. -
Overdue preventive maintenance plans. - Total downtime in the selected
period. - Preventive maintenance completion rate.

**Charts and tables** - Downtime by equipment. - Work orders by
status. - Maintenance activity over time. - Top equipment by downtime. -
Upcoming and overdue maintenance. - Recent work orders.

**KPI definitions**

**Downtime** - Sum of downtime durations in the selected period. - For
open incidents, calculate duration up to the current time. - Define
clearly whether the selected period filters by incident start time or
overlap with the period. For the MVP, use incident start time.

**MTTR (Mean Time To Repair)** - Sum of completed corrective repair
durations divided by the number of completed corrective work orders with
valid start and completion timestamps. - Repair duration =
`completed_at - started_at`. - Exclude incomplete records and show the
sample count.

**MTBF (Mean Time Between Failures)** - For the MVP, use an explicitly
documented approximation: -
`Estimated operating hours / number of qualifying breakdown incidents`. -
The demo organization has a configurable assumed operating-hours-per-day
value. - Do not present this as sensor-measured operating time. - If
there are no qualifying breakdowns, return `null` / "Not enough data",
not infinity.

**Preventive maintenance completion rate** - Completed preventive work
orders divided by all preventive work orders due in the selected period,
multiplied by 100. - Clearly document the denominator and avoid counting
cancelled work orders as completed.

**Analytics requirements** - All calculations must be
organization-scoped. - Support a date range filter. - Return zero or an
explicit no-data state where appropriate. - Use decimal/consistent units
and document rounding. - Optimize ORM queries and avoid N+1 queries.

### 3.7 Audit and history

Record important events: - Equipment created, updated, or retired. -
Maintenance plan created, updated, or deactivated. - Work order assigned
and status changed. - Downtime opened and closed. - User activated or
deactivated.

An audit record should include organization, actor, action, entity type,
entity ID, timestamp, and a compact JSON metadata payload. Do not store
passwords, tokens, or sensitive authentication data.

------------------------------------------------------------------------

## 4. Non-functional requirements

### 4.1 Security

-   Use environment variables for secrets and database credentials.
-   Never commit `.env` files.
-   Use Django password hashing.
-   Validate all input on the backend.
-   Apply authentication, role checks, and organization scoping.
-   Configure CORS for the known frontend origin.
-   Use HTTPS in production.
-   Set secure cookie/header and Django production settings
    appropriately.
-   Avoid exposing stack traces or secrets in production responses.

### 4.2 Reliability and data integrity

-   Add database constraints for organization-scoped unique identifiers
    where appropriate.
-   Use transactions for multi-record business operations.
-   Use idempotency safeguards for scheduled maintenance generation.
-   Use timezone-aware datetimes.
-   Add automated tests for critical business rules.

### 4.3 Performance

-   Paginate list endpoints.
-   Add indexes for common filters, organization IDs, statuses, and due
    dates.
-   Use `select_related` and `prefetch_related` where appropriate.
-   Use ORM aggregation for analytics rather than fetching all records
    into Python.
-   Inspect query counts for dashboard and list endpoints.

### 4.4 Usability

-   Responsive desktop-first interface.
-   Consistent navigation and page layout.
-   Loading, empty, success, and error states.
-   Confirmation before destructive or irreversible actions.
-   Clear status and priority labels.
-   Form validation with understandable messages.

------------------------------------------------------------------------

## 5. Data model overview

The following is the conceptual model. Exact field types and constraints
are finalized during Phase 1.

  -----------------------------------------------------------------------
  Model                   Important relationships Notes
  ----------------------- ----------------------- -----------------------
  Organization            Has many users and      Tenant boundary
                          operational records     

  User                    Belongs to an           Custom Django user;
                          organization            role field

  EquipmentCategory       Belongs to an           Organization-specific
                          organization            categories

  Equipment               Belongs to organization Unique equipment code
                          and category            per organization

  MaintenancePlan         Belongs to organization Recurrence and next due
                          and equipment           date

  WorkOrder               Belongs to organization Optional plan and
                          and equipment           assigned technician

  WorkOrderHistory        Belongs to work order   Workflow history
                          and actor               

  DowntimeRecord          Belongs to organization Optional related work
                          and equipment           order

  AuditLog                Belongs to organization Important system events
                          and actor               
  -----------------------------------------------------------------------

**Important modeling decisions** - Use a custom Django user model from
the beginning, before the first migration. - Use explicit foreign keys
to Organization on tenant-owned models, even if organization can be
derived through another relationship. This supports clear scoping and
integrity checks. - Add database constraints for organization-scoped
uniqueness. - Ensure related foreign keys (equipment, technician, plan)
belong to the same organization through service validation and tests. A
normal foreign key alone does not enforce this cross-table rule. -
Prefer deactivation/retirement over deleting operational history.

------------------------------------------------------------------------

## 6. API design

Base path: `/api/v1/`

### 6.1 Authentication and profile

  Method   Endpoint                 Purpose
  -------- ------------------------ ----------------------------------
  POST     `/auth/token/`           Obtain JWT pair
  POST     `/auth/token/refresh/`   Refresh access token
  GET      `/auth/me/`              Current user and organization
  GET      `/users/`                List organization users (admin)
  POST     `/users/`                Create organization user (admin)
  PATCH    `/users/{id}/`           Update user (admin)

### 6.2 Equipment

  Method   Endpoint                     Purpose
  -------- ---------------------------- ------------------------------
  GET      `/equipment/`                List/search/filter equipment
  POST     `/equipment/`                Create equipment
  GET      `/equipment/{id}/`           Equipment detail
  PATCH    `/equipment/{id}/`           Update equipment
  POST     `/equipment/{id}/retire/`    Retire equipment
  GET      `/equipment/{id}/history/`   Related maintenance history

Suggested query parameters: `search`, `status`, `category`, `location`,
`page`.

### 6.3 Maintenance plans

  Method   Endpoint                                Purpose
  -------- --------------------------------------- -----------------
  GET      `/maintenance-plans/`                   List plans
  POST     `/maintenance-plans/`                   Create plan
  GET      `/maintenance-plans/{id}/`              Plan detail
  PATCH    `/maintenance-plans/{id}/`              Update plan
  POST     `/maintenance-plans/{id}/deactivate/`   Deactivate plan
  GET      `/maintenance-plans/calendar/`          Due-date view

Suggested filters: `status`, `due_before`, `due_after`, `equipment`.

### 6.4 Work orders

  Method   Endpoint                        Purpose
  -------- ------------------------------- -------------------------
  GET      `/work-orders/`                 List work orders
  POST     `/work-orders/`                 Create work order
  GET      `/work-orders/{id}/`            Detail
  PATCH    `/work-orders/{id}/`            Update permitted fields
  POST     `/work-orders/{id}/assign/`     Assign technician
  POST     `/work-orders/{id}/start/`      Start work
  POST     `/work-orders/{id}/complete/`   Complete work
  POST     `/work-orders/{id}/cancel/`     Cancel work
  GET      `/work-orders/{id}/history/`    Workflow history

Use explicit action endpoints for state transitions rather than allowing
arbitrary status changes through a generic PATCH request.

### 6.5 Downtime

  Method   Endpoint                            Purpose
  -------- ----------------------------------- ------------------
  GET      `/downtime-records/`                List incidents
  POST     `/downtime-records/`                Record breakdown
  GET      `/downtime-records/{id}/`           Detail
  POST     `/downtime-records/{id}/recover/`   Record recovery

### 6.6 Analytics

  -------------------------------------------------------------------------------------
  Method                  Endpoint                              Purpose
  ----------------------- ------------------------------------- -----------------------
  GET                     `/analytics/overview/`                Summary cards

  GET                     `/analytics/downtime/`                Downtime chart data

  GET                     `/analytics/work-orders/`             Work-order status and
                                                                trend

  GET                     `/analytics/maintenance/`             Preventive maintenance
                                                                metrics

  GET                     `/analytics/equipment-performance/`   Equipment ranking and
                                                                KPIs
  -------------------------------------------------------------------------------------

Analytics endpoints accept `start_date` and `end_date`.

### 6.7 API conventions

-   Use consistent JSON response structures.
-   Use appropriate HTTP status codes.
-   Return field-level validation errors.
-   Use pagination for collections.
-   Document endpoints and schemas using OpenAPI/Swagger.
-   Never accept organization ownership from an untrusted client field.
-   Ensure all endpoint querysets are organization-scoped.

------------------------------------------------------------------------

## 7. Frontend specification

### 7.1 Main navigation

-   Dashboard
-   Equipment
-   Maintenance Plans
-   Work Orders
-   Downtime
-   Analytics
-   Users (admin only)
-   Profile / Logout

Navigation items should be hidden when the role cannot use them, but the
backend remains the authority for access control.

### 7.2 Pages and key interactions

  -----------------------------------------------------------------------
  Page                                Main UI elements
  ----------------------------------- -----------------------------------
  Login                               Email, password, validation

  Dashboard                           KPI cards, charts, alerts, recent
                                      work orders

  Equipment list                      Search, filters, pagination,
                                      create/edit

  Equipment detail                    Metadata, status, maintenance and
                                      downtime history

  Maintenance plans                   Plan list, due status, create/edit,
                                      calendar/list

  Work orders                         Filters, status tabs, create,
                                      assign, start, complete

  Work order detail                   Description, equipment, assignee,
                                      timeline, completion form

  Downtime                            Incident list, record breakdown,
                                      record recovery

  Analytics                           Date filters, KPI cards, charts,
                                      rankings

  Users                               User list, create user, role and
                                      active status
  -----------------------------------------------------------------------

### 7.3 Frontend engineering rules

-   Use TypeScript types for API data.
-   Use a shared API client.
-   Use TanStack Query for server state, caching, invalidation, and
    loading/error states.
-   Keep form state separate from server state.
-   Validate forms with Zod and React Hook Form.
-   Do not duplicate business rules in the frontend as the only
    enforcement.
-   Handle expired JWT access tokens with a refresh flow.
-   Avoid storing long-lived sensitive tokens in insecure browser
    storage if a safer deployment design is available. For a time-boxed
    demo, document the chosen token-storage trade-off.

------------------------------------------------------------------------

## 8. Recommended repository structure

``` text
maintenx/
├── backend/
│   ├── config/
│   │   ├── settings/
│   │   ├── urls.py
│   │   ├── celery.py
│   │   └── asgi.py
│   ├── apps/
│   │   ├── accounts/
│   │   ├── organizations/
│   │   ├── equipment/
│   │   ├── maintenance/
│   │   ├── work_orders/
│   │   ├── downtime/
│   │   ├── analytics/
│   │   └── audit_logs/
│   ├── common/
│   ├── tests/
│   ├── requirements/
│   ├── manage.py
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   ├── components/
│   │   ├── features/
│   │   ├── hooks/
│   │   ├── lib/
│   │   ├── routes/
│   │   └── types/
│   └── Dockerfile
├── docs/
│   ├── architecture.md
│   ├── database-design.md
│   └── api-guide.md
├── .env.example
├── .gitignore
├── docker-compose.yml
└── README.md
```

Keep the project modular, but do not over-engineer it into microservices
or force a complex Clean Architecture structure onto a one-week Django
MVP.

------------------------------------------------------------------------

# 9. Seven-day implementation plan: Phase 0 to completion

The schedule is an intensive, time-boxed plan. The order matters: get a
thin end-to-end application working early, then deepen each module. If
time becomes tight, protect the core workflow and testing before adding
visual polish.

## Phase 0 --- Environment setup and project initialization

**Target:** Day 1, first part\
**Outcome:** Local development environment runs; Django, React,
PostgreSQL, and Redis are available.

### 0.1 Install prerequisites

Install and verify:

1.  **Python 3.12 or a currently supported compatible version**
    -   Verify: `python --version`
    -   On Windows, the launcher may be `py --version`.
2.  **Node.js LTS and npm**
    -   Verify: `node --version`
    -   Verify: `npm --version`
3.  **Git**
    -   Verify: `git --version`
4.  **Docker Desktop**
    -   Enable its WSL 2 backend on Windows if prompted.
    -   Verify: `docker --version`
    -   Verify: `docker compose version`
5.  **Code editor**
    -   VS Code or another editor.
    -   Useful extensions: Python, Pylance, ESLint, Prettier, Docker,
        PostgreSQL (optional).
6.  **API testing tool**
    -   Postman, Insomnia, or VS Code REST Client.
    -   Browser access to Swagger UI will also be used later.
7.  **PostgreSQL client (optional)**
    -   DBeaver or pgAdmin. PostgreSQL itself will run in Docker.

### 0.2 Create the repository

``` bash
mkdir maintenx
cd maintenx
git init

mkdir backend frontend docs
```

Create `.gitignore` before adding application files. Ignore at minimum:

``` gitignore
.env
.venv/
__pycache__/
*.py[cod]
.pytest_cache/
.coverage
htmlcov/
node_modules/
dist/
.vite/
.idea/
.vscode/
.DS_Store
```

Do not ignore committed dependency lock files.

### 0.3 Create the environment file

Create `.env.example` with placeholders:

``` dotenv
DJANGO_SECRET_KEY=replace-me
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
POSTGRES_DB=maintenx
POSTGRES_USER=maintenx
POSTGRES_PASSWORD=replace-me
POSTGRES_HOST=db
POSTGRES_PORT=5432
REDIS_URL=redis://redis:6379/0
CORS_ALLOWED_ORIGINS=http://localhost:5173
TIME_ZONE=Asia/Jakarta
```

Copy it to `.env` for local development and replace placeholder secrets.
Never commit `.env`.

### 0.4 Initialize Django

From the repository root:

``` bash
cd backend
python -m venv .venv
```

Activate the virtual environment:

**Windows PowerShell**

``` powershell
.venv\Scripts\Activate.ps1
```

**macOS/Linux**

``` bash
source .venv/bin/activate
```

Install the initial backend dependencies:

``` bash
python -m pip install --upgrade pip
pip install Django djangorestframework "psycopg[binary]" djangorestframework-simplejwt django-filter django-cors-headers drf-spectacular celery redis django-environ
pip install pytest pytest-django coverage
```

Save dependencies:

``` bash
pip freeze > requirements/dev.txt
```

Create the Django project:

``` bash
django-admin startproject config .
```

Create app modules as needed during Phase 1 rather than generating empty
apps that are not yet understood.

### 0.5 Initialize React

From the repository root:

``` bash
cd frontend
npm create vite@latest . -- --template react-ts
npm install
```

Install core frontend dependencies:

``` bash
npm install react-router-dom @tanstack/react-query axios recharts react-hook-form zod @hookform/resolvers lucide-react
```

Install Tailwind CSS using the current official Vite integration
instructions for the selected Tailwind major version. Do not mix
configuration instructions from different Tailwind versions.

Initialize shadcn/ui using its current Vite + React + TypeScript setup
guide. Add only the components actually needed.

Run the frontend:

``` bash
npm run dev
```

Confirm the Vite page loads at `http://localhost:5173`.

### 0.6 Add Docker Compose services

Create a `docker-compose.yml` with at least: - `db`: PostgreSQL. -
`redis`: Redis. - Optional later: `backend`, `celery_worker`,
`celery_beat`, and `frontend`.

For the first local setup, it is acceptable to run Django and Vite
directly on the host while PostgreSQL and Redis run in Docker. This
reduces early debugging complexity. Containerize the full application
once the local workflow is stable.

Example initial infrastructure-only Compose file:

``` yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 5s
      timeout: 5s
      retries: 10

  redis:
    image: redis:7
    ports:
      - "6379:6379"

volumes:
  postgres_data:
```

Start infrastructure from the repository root:

``` bash
docker compose up -d
docker compose ps
```

### Phase 0 exit checklist

-   [ ] Python virtual environment activates.
-   [ ] Django project starts.
-   [ ] React/Vite project starts.
-   [ ] PostgreSQL container is healthy.
-   [ ] Redis container is running.
-   [ ] `.env` is not tracked by Git.
-   [ ] Initial Git commit exists.

------------------------------------------------------------------------

## Phase 1 --- Backend foundation, data model, and authentication

**Target:** Day 1, remaining time\
**Outcome:** Users can authenticate and access only their own
organization's data.

### Tasks

1.  Configure Django settings and environment variables.
2.  Configure PostgreSQL connection.
3.  Configure DRF, JWT, CORS, filtering, pagination, and OpenAPI.
4.  Create the custom user model before running the first migration.
5.  Create Organization and membership/role relationship.
6.  Create common organization-scoping and permission utilities.
7.  Create initial apps:
    -   `accounts`
    -   `organizations`
    -   `equipment`
    -   `maintenance`
    -   `work_orders`
    -   `downtime`
    -   `analytics`
    -   `audit_logs`
8.  Implement token, refresh, and current-user endpoints.
9.  Implement admin-only user creation within the current organization.
10. Write tests for authentication, roles, and tenant isolation.

### Important implementation order

-   Define `AUTH_USER_MODEL` before the first migration.
-   Create Organization and user membership models.
-   Run migrations.
-   Create a development organization and users.
-   Implement a reusable organization-scoped queryset pattern.
-   Test that User A cannot retrieve Organization B's records.

### Commands

``` bash
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

### Phase 1 exit checklist

-   [ ] Database migrations succeed.
-   [ ] Admin and test users can be created.
-   [ ] JWT login and refresh work.
-   [ ] `/api/v1/auth/me/` returns the current profile.
-   [ ] Protected endpoints reject anonymous users.
-   [ ] Cross-organization access tests pass.

------------------------------------------------------------------------

## Phase 2 --- Equipment management

**Target:** Day 2\
**Outcome:** Admins and managers can manage equipment; technicians can
view it.

### Backend tasks

1.  Implement EquipmentCategory and Equipment models.
2.  Add organization-scoped unique equipment codes.
3.  Implement serializers and validation.
4.  Implement list, detail, create, update, and retire endpoints.
5.  Add search, filters, ordering, and pagination.
6.  Scope every queryset by organization.
7.  Add equipment history endpoint.
8.  Add tests for permissions, validation, filtering, and tenant
    isolation.

### Frontend tasks

1.  Create shared application layout and navigation.
2.  Create login page and protected routes.
3.  Implement shared API client and authentication state.
4.  Create equipment list page.
5.  Create equipment form.
6.  Create equipment detail page.
7.  Add search, filters, pagination, loading and empty states.

### Phase 2 exit checklist

-   [ ] Admin/manager can create and edit equipment.
-   [ ] Technician can view equipment but cannot edit it.
-   [ ] Duplicate equipment codes are rejected within an organization.
-   [ ] Retired equipment cannot receive new operational records.
-   [ ] Equipment list and detail work through real APIs.

------------------------------------------------------------------------

## Phase 3 --- Preventive maintenance scheduling

**Target:** Day 3\
**Outcome:** Managers can define recurring maintenance and the system
can identify due plans and generate work orders safely.

### Backend tasks

1.  Implement MaintenancePlan model.
2.  Implement frequency and next-due-date calculations in a dedicated
    service.
3.  Implement create, list, detail, update, and deactivate endpoints.
4.  Implement upcoming/due/overdue filters.
5.  Configure Celery application and Redis broker.
6.  Add a daily task to identify due plans.
7.  Add idempotency protection so one plan cannot generate duplicate
    work orders for the same due date.
8.  Add tests for recurrence, overdue logic, and repeated task
    execution.

### Frontend tasks

1.  Build maintenance-plan list.
2.  Build create/edit plan forms.
3.  Display due status and next due date.
4.  Add filters for upcoming, due, overdue, and inactive plans.
5.  Add a calendar-style view only if the list workflow is already
    complete.

### Phase 3 exit checklist

-   [ ] Daily, weekly, and monthly plans can be created.
-   [ ] Next due date is calculated correctly.
-   [ ] Overdue plans are identified correctly.
-   [ ] Scheduled task runs successfully.
-   [ ] Running the task twice does not create duplicate work orders.

------------------------------------------------------------------------

## Phase 4 --- Work-order workflow

**Target:** Day 4\
**Outcome:** Managers can create and assign work; technicians can
execute and complete assigned work.

### Backend tasks

1.  Implement WorkOrder and WorkOrderHistory models.
2.  Generate unique work-order numbers per organization.
3.  Implement list, detail, and create endpoints.
4.  Implement explicit assign, start, complete, and cancel actions.
5.  Validate legal state transitions on the server.
6.  Restrict technician actions to assigned work orders.
7.  Record actor, timestamp, and status changes.
8.  Use database transactions for completion operations.
9.  Add tests for every allowed and disallowed transition.

### Frontend tasks

1.  Build work-order list with status and priority filters.
2.  Build work-order creation form.
3.  Build assignment interaction.
4.  Build work-order detail and activity timeline.
5.  Add technician actions: start and complete.
6.  Add completion notes and labor-time fields.
7.  Display status and permission-specific actions.

### Phase 4 exit checklist

-   [ ] Manager can create and assign a work order.
-   [ ] Technician sees their assigned work orders.
-   [ ] Technician cannot update another technician's work order.
-   [ ] Invalid status transitions are rejected.
-   [ ] Completion requires notes and records timestamps.
-   [ ] Work-order history is recorded.

------------------------------------------------------------------------

## Phase 5 --- Downtime tracking and analytics

**Target:** Day 5\
**Outcome:** The system records equipment breakdowns and computes
meaningful maintenance metrics.

### Backend tasks

1.  Implement DowntimeRecord model.
2.  Implement breakdown and recovery endpoints.
3.  Validate timestamps and prevent overlapping open incidents.
4.  Implement downtime duration calculations.
5.  Implement analytics service functions.
6.  Implement overview, downtime, work-order, maintenance, and
    equipment-performance endpoints.
7.  Add date-range filtering.
8.  Use ORM aggregation and annotations.
9.  Add tests with known sample data and expected KPI values.

### Frontend tasks

1.  Build downtime list and incident form.
2.  Add recovery action.
3.  Build dashboard KPI cards.
4.  Add downtime-by-equipment chart.
5.  Add work-order status chart.
6.  Add maintenance completion metric.
7.  Build analytics page with date-range filters.
8.  Show no-data and sample-count states for KPIs.

### Phase 5 exit checklist

-   [ ] Breakdown can be recorded.
-   [ ] Recovery closes an incident and computes duration.
-   [ ] Invalid or overlapping incidents are rejected.
-   [ ] MTTR and MTBF calculations match documented definitions.
-   [ ] Analytics are based on database records and scoped to the
    organization.
-   [ ] Dashboard charts render real API data.

------------------------------------------------------------------------

## Phase 6 --- Integration, testing, and hardening

**Target:** Day 6\
**Outcome:** The main user journeys work end-to-end and critical backend
behavior is tested.

### Integration tasks

1.  Connect all frontend pages to their API endpoints.
2.  Check JWT refresh and expired-session handling.
3.  Check role-specific navigation and actions.
4.  Standardize API error handling.
5.  Check forms and server-side validation messages.
6.  Add loading, empty, success, and failure states.
7.  Verify responsive layout at desktop and tablet widths.

### Backend test priorities

-   Authentication and inactive users.
-   Organization data isolation for every major resource.
-   Role and object-level permissions.
-   Equipment uniqueness and retirement.
-   Maintenance recurrence and idempotency.
-   Work-order transition rules.
-   Downtime validation and duration.
-   KPI calculations and date boundaries.

### Quality checks

``` bash
# Backend
pytest
python manage.py check
python manage.py makemigrations --check --dry-run

# Frontend
npm run build
```

Run the frontend commands from `frontend/` and backend commands from
`backend/`.

Inspect API query counts for dashboard and list endpoints. Add indexes
and `select_related` / `prefetch_related` where justified.

### Phase 6 exit checklist

-   [ ] Admin journey works from login through user/equipment setup.
-   [ ] Manager journey works from maintenance plan through work-order
    assignment.
-   [ ] Technician journey works from assigned work through completion.
-   [ ] Downtime and analytics update from recorded events.
-   [ ] Critical automated tests pass.
-   [ ] Production frontend build succeeds.
-   [ ] No secrets are committed.

------------------------------------------------------------------------

## Phase 7 --- Docker, deployment, documentation, and demo

**Target:** Day 7\
**Outcome:** A recruiter can open the deployed project, understand it,
and try the core workflow.

### Docker and deployment tasks

1.  Add backend Dockerfile.
2.  Add frontend Dockerfile or production static build configuration.
3.  Add Celery worker and Celery Beat services.
4.  Configure Compose service dependencies and health checks.
5.  Configure production environment variables.
6.  Configure Django `DEBUG=False`, allowed hosts, CORS, and CSRF
    trusted origins as required.
7.  Configure static files and frontend API base URL.
8.  Run database migrations during deployment using a controlled release
    step.
9.  Deploy to a suitable hosting provider.
10. Verify HTTPS and production logs.

Do not use the development Django server as the production application
server. Use a production WSGI/ASGI server appropriate to the deployment.

### Seed demo data

Create a management command such as:

``` bash
python manage.py seed_demo_data
```

Include: - One demo organization. - One admin, one manager, and two
technicians. - 15--25 pieces of equipment across several categories. - A
mixture of operational and out-of-service equipment. - Several
maintenance plans: upcoming, due, and overdue. - Work orders in
different workflow states. - Completed and open downtime incidents. -
Enough history to make charts meaningful.

Use clearly fictional demo data. Document demo credentials publicly only
if the deployment is intended for public demo access, and never reuse
real credentials.

### Documentation tasks

README should include: - Product problem and solution. - Screenshots or
short demo GIF/video. - Feature list. - Technology stack. - Architecture
diagram. - Local setup instructions. - Environment variable reference. -
Test instructions. - Demo account instructions. - API documentation
link. - Known limitations and future improvements.

### Final exit checklist

-   [ ] Production frontend is reachable.
-   [ ] Production API is reachable.
-   [ ] Swagger/OpenAPI documentation is available.
-   [ ] Demo accounts work.
-   [ ] Seeded data makes the product understandable.
-   [ ] Celery worker and scheduler are running.
-   [ ] Core workflow works in production.
-   [ ] README is complete.
-   [ ] GitHub repository is presentable.
-   [ ] Short product demo is recorded.

------------------------------------------------------------------------

## 10. Recommended daily working rhythm

Use this as a guide, not a requirement to work without breaks.

  -----------------------------------------------------------------------
  Work block                          Focus
  ----------------------------------- -----------------------------------
  30--45 min                          Read the day's requirements and
                                      understand the domain rules

  2--3 hours                          Implement backend models, services,
                                      serializers, and APIs

  1--2 hours                          Write and run backend tests

  1--2 hours                          Implement React pages and API
                                      integration

  30--60 min                          Test the full workflow, fix
                                      defects, update documentation
  -----------------------------------------------------------------------

At the end of each day: - Commit working code. - Record unfinished
tasks. - Keep the application runnable. - Do not begin the next phase
with a broken baseline if it can be avoided.

------------------------------------------------------------------------

## 11. Development conventions

### Django

-   Use a custom user model from the beginning.
-   Keep views thin.
-   Put non-trivial business rules in service modules.
-   Use serializers for input/output validation, not as the only home
    for all business logic.
-   Use explicit permission classes.
-   Scope querysets by organization.
-   Use transactions for multi-step writes.
-   Add tests alongside each feature.
-   Use migrations for all schema changes.

### React

-   Use feature-based folders.
-   Keep reusable UI components separate from domain pages.
-   Use typed API response models.
-   Centralize API configuration and error handling.
-   Use TanStack Query for server state.
-   Keep components focused and reasonably small.
-   Avoid duplicating backend business rules.

### Git

Use small, descriptive commits, for example:

``` text
chore: initialize django and react projects
feat(auth): add jwt authentication
feat(organizations): enforce tenant data isolation
feat(equipment): add equipment management endpoints
feat(maintenance): add preventive maintenance plans
feat(work-orders): implement assignment workflow
feat(downtime): add breakdown and recovery tracking
feat(analytics): add maintenance KPI endpoints
test: cover tenant isolation and work order transitions
docs: add setup and API documentation
```

------------------------------------------------------------------------

## 12. MVP acceptance criteria

The MVP is complete when a reviewer can:

1.  Log in as an organization admin.
2.  Create a manager and technicians.
3.  Register equipment.
4.  Create a preventive maintenance plan.
5.  See a due plan generate a work order without duplicates.
6.  Assign the work order to a technician.
7.  Log in as that technician and start the work.
8.  Complete the work with notes.
9.  Record a breakdown and subsequent recovery.
10. View downtime and maintenance KPIs on the dashboard.
11. Verify that a user from another organization cannot access these
    records.
12. Read the API documentation and run the project using the README.

------------------------------------------------------------------------

## 13. Risks and scope fallback

Seven days is a short delivery window. Prioritize in this order if
implementation takes longer than expected:

**Must have** - Authentication and organization isolation. - Equipment
management. - Work orders and technician assignment. - Downtime
recording. - Basic dashboard metrics. - Tests for permissions and
critical business rules.

**Should have** - Preventive maintenance recurrence. - Celery scheduled
generation. - MTTR and MTBF. - Analytics charts. - Dockerized full
application.

**Can be simplified** - Calendar UI (use a filtered list). - Advanced
audit-log browsing (persist history but show a basic timeline). -
Extensive user administration. - Elaborate chart interactions. - Fancy
animations and visual effects.

Do not sacrifice tenant isolation, server-side validation, or core
workflow tests to finish decorative frontend work.

------------------------------------------------------------------------

## 14. Suggested future roadmap

After the MVP is complete and validated with potential users:

-   Spare-parts and inventory management.
-   QR codes on equipment for quick lookup.
-   Technician mobile-friendly workflow / PWA.
-   Email notifications for due and overdue maintenance.
-   Custom maintenance checklists.
-   Attachments and repair photos.
-   Equipment cost and lifecycle reporting.
-   CSV/PDF exports.
-   Multiple facilities per organization.
-   Sensor/IoT integrations.
-   Predictive maintenance after sufficient historical data exists.

**Product principle:** Build the operational record and reliable data
pipeline first. Predictive features are only credible when the system
has enough trustworthy historical data.
