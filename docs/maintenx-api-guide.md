# MaintenX --- API Guide

## 1. Overview

MaintenX exposes a versioned REST API through Django REST Framework.

-   Base URL (local): `http://localhost:8000/api/v1/`
-   Content type: `application/json`
-   Authentication: JWT bearer access token
-   API documentation: OpenAPI/Swagger through `drf-spectacular`

All endpoints that access organization data must derive the organization
from the authenticated user and scope the queryset accordingly.

## 2. Authentication

### Obtain token

`POST /api/v1/auth/token/`

Request:

``` json
{
  "email": "manager@example.com",
  "password": "demo-password"
}
```

Response (illustrative):

``` json
{
  "access": "<access-token>",
  "refresh": "<refresh-token>"
}
```

Use the access token:

``` http
Authorization: Bearer <access-token>
```

### Refresh token

`POST /api/v1/auth/token/refresh/`

``` json
{
  "refresh": "<refresh-token>"
}
```

### Current user

`GET /api/v1/auth/me/`

Illustrative response:

``` json
{
  "id": "user-uuid",
  "email": "manager@example.com",
  "first_name": "Demo",
  "last_name": "Manager",
  "role": "MANAGER",
  "organization": {
    "id": "organization-uuid",
    "name": "Demo Manufacturing",
    "timezone": "Asia/Jakarta"
  }
}
```

The organization in the response is informational. Clients must not use
it as an authorization override.

## 3. Roles

-   `ADMIN`: user administration and all organization operations.
-   `MANAGER`: operational management, equipment, maintenance plans,
    work orders, downtime, and analytics.
-   `TECHNICIAN`: view equipment and plans, view assigned work orders,
    perform permitted work-order actions, and record permitted downtime
    activity.

The backend enforces permissions. Hiding a button in React is not
security.

## 4. Endpoint catalogue

### Authentication and users

  Method   Path                     Access                Purpose
  -------- ------------------------ --------------------- -------------------------------------
  POST     `/auth/token/`           Public                Login
  POST     `/auth/token/refresh/`   Valid refresh token   Refresh access
  GET      `/auth/me/`              Authenticated         Current profile
  GET      `/users/`                Admin                 List organization users
  POST     `/users/`                Admin                 Create user in current organization
  PATCH    `/users/{id}/`           Admin                 Update permitted user fields

### Equipment

  Method   Path                         Access           Purpose
  -------- ---------------------------- ---------------- --------------------
  GET      `/equipment/`                All roles        List/search/filter
  POST     `/equipment/`                Admin, Manager   Create
  GET      `/equipment/{id}/`           All roles        Detail
  PATCH    `/equipment/{id}/`           Admin, Manager   Update
  POST     `/equipment/{id}/retire/`    Admin, Manager   Retire
  GET      `/equipment/{id}/history/`   All roles        Related history

Query parameters: - `search`: equipment code, name, serial number, or
location. - `status`: equipment status. - `category`: category ID. -
`location`: location filter. - `page`: page number.

### Maintenance plans

  ---------------------------------------------------------------------------------------------
  Method            Path                                    Access            Purpose
  ----------------- --------------------------------------- ----------------- -----------------
  GET               `/maintenance-plans/`                   All roles         List plans

  POST              `/maintenance-plans/`                   Admin, Manager    Create

  GET               `/maintenance-plans/{id}/`              All roles         Detail

  PATCH             `/maintenance-plans/{id}/`              Admin, Manager    Update

  POST              `/maintenance-plans/{id}/deactivate/`   Admin, Manager    Deactivate

  GET               `/maintenance-plans/calendar/`          All roles         Due-date data
  ---------------------------------------------------------------------------------------------

Query parameters: `status`, `due_before`, `due_after`, `equipment`,
`page`.

### Work orders

  -------------------------------------------------------------------------------------
  Method            Path                            Access            Purpose
  ----------------- ------------------------------- ----------------- -----------------
  GET               `/work-orders/`                 Role-scoped       List

  POST              `/work-orders/`                 Admin, Manager    Create

  GET               `/work-orders/{id}/`            Role-scoped       Detail

  PATCH             `/work-orders/{id}/`            Admin, Manager;   Update
                                                    restricted fields 

  POST              `/work-orders/{id}/assign/`     Admin, Manager    Assign technician

  POST              `/work-orders/{id}/start/`      Assigned          Start work
                                                    technician;       
                                                    Admin/Manager     

  POST              `/work-orders/{id}/complete/`   Assigned          Complete
                                                    technician;       
                                                    Admin/Manager     

  POST              `/work-orders/{id}/cancel/`     Admin, Manager    Cancel

  GET               `/work-orders/{id}/history/`    Role-scoped       Timeline
  -------------------------------------------------------------------------------------

Do not expose arbitrary status changes through generic PATCH. Use the
action endpoints to validate the state machine.

### Downtime

  -----------------------------------------------------------------------------------------
  Method            Path                                Access            Purpose
  ----------------- ----------------------------------- ----------------- -----------------
  GET               `/downtime-records/`                Role-scoped       List incidents

  POST              `/downtime-records/`                Admin, Manager,   Record breakdown
                                                        permitted         
                                                        Technician        

  GET               `/downtime-records/{id}/`           Role-scoped       Detail

  POST              `/downtime-records/{id}/recover/`   Admin, Manager,   Record recovery
                                                        permitted         
                                                        Technician        
  -----------------------------------------------------------------------------------------

### Analytics

  -------------------------------------------------------------------------------------------
  Method            Path                                  Access            Purpose
  ----------------- ------------------------------------- ----------------- -----------------
  GET               `/analytics/overview/`                Admin, Manager    KPI summary

  GET               `/analytics/downtime/`                Admin, Manager    Downtime chart

  GET               `/analytics/work-orders/`             Admin, Manager    Work-order chart

  GET               `/analytics/maintenance/`             Admin, Manager    Preventive
                                                                            maintenance
                                                                            metrics

  GET               `/analytics/equipment-performance/`   Admin, Manager    Equipment ranking
  -------------------------------------------------------------------------------------------

Date-filtered endpoints accept `start_date=YYYY-MM-DD` and
`end_date=YYYY-MM-DD`. Validate that start is not after end and define
date boundaries in the organization's timezone.

## 5. Example requests

### Create equipment

`POST /api/v1/equipment/`

``` json
{
  "equipment_code": "CNC-001",
  "name": "CNC Milling Machine",
  "category": "category-uuid",
  "manufacturer": "Example Industrial",
  "model_number": "MX-200",
  "location": "Production Hall A",
  "status": "OPERATIONAL"
}
```

Do not send `organization_id`; the backend assigns it from the
authenticated user.

### Create maintenance plan

`POST /api/v1/maintenance-plans/`

``` json
{
  "equipment": "equipment-uuid",
  "title": "Monthly lubrication inspection",
  "description": "Inspect lubrication system and record findings.",
  "frequency": "MONTHLY",
  "interval_value": 1,
  "start_date": "2026-11-03",
  "next_due_date": "2026-11-03",
  "estimated_duration_minutes": 45,
  "default_technician": "technician-uuid"
}
```

### Create corrective work order

`POST /api/v1/work-orders/`

``` json
{
  "equipment": "equipment-uuid",
  "title": "Machine vibration investigation",
  "description": "Investigate abnormal vibration during operation.",
  "work_order_type": "CORRECTIVE",
  "priority": "HIGH",
  "due_date": "2026-11-04"
}
```

### Assign technician

`POST /api/v1/work-orders/{id}/assign/`

``` json
{
  "technician_id": "technician-uuid"
}
```

### Start work

`POST /api/v1/work-orders/{id}/start/`

``` json
{}
```

The server records `started_at`.

### Complete work

`POST /api/v1/work-orders/{id}/complete/`

``` json
{
  "completion_notes": "Replaced worn coupling and tested machine operation.",
  "actual_labor_minutes": 75
}
```

The server validates the current state and records `completed_at`.

### Record breakdown

`POST /api/v1/downtime-records/`

``` json
{
  "equipment": "equipment-uuid",
  "work_order": "work-order-uuid",
  "reason": "MECHANICAL",
  "description": "Unexpected coupling failure.",
  "started_at": "2026-11-03T02:15:00Z"
}
```

### Record recovery

`POST /api/v1/downtime-records/{id}/recover/`

``` json
{
  "ended_at": "2026-11-03T04:00:00Z",
  "recovery_notes": "Coupling replaced; test run successful."
}
```

The backend validates that the recovery time is not before the start
time.

## 6. Example analytics response

`GET /api/v1/analytics/overview/?start_date=2026-11-01&end_date=2026-11-30`

Illustrative response:

``` json
{
  "period": {
    "start_date": "2026-11-01",
    "end_date": "2026-11-30"
  },
  "equipment": {
    "active_count": 24
  },
  "work_orders": {
    "open_count": 5
  },
  "maintenance": {
    "overdue_plan_count": 2,
    "completion_rate_percent": 87.5,
    "completed_count": 14,
    "due_count": 16
  },
  "downtime": {
    "total_hours": 12.5,
    "incident_count": 4
  },
  "mttr": {
    "hours": 1.8,
    "sample_count": 5
  },
  "mtbf": {
    "hours": 120.0,
    "sample_count": 4,
    "method": "estimated_operating_hours_divided_by_breakdown_count"
  }
}
```

Values above are examples only. The API must calculate values from
database records and return the actual sample counts.

## 7. Filtering, pagination, and sorting

Use consistent pagination, for example:

``` json
{
  "count": 42,
  "next": "http://localhost:8000/api/v1/equipment/?page=2",
  "previous": null,
  "results": []
}
```

Support only documented filters. Validate ordering fields against an
allowlist to avoid exposing unintended model fields.

## 8. Error response conventions

Use appropriate HTTP status codes: - `400 Bad Request`: invalid fields
or business rule. - `401 Unauthorized`: missing or invalid
authentication. - `403 Forbidden`: authenticated user lacks
permission. - `404 Not Found`: object absent or outside the user's
organization. - `409 Conflict`: conflicting state or duplicate operation
where appropriate. - `429 Too Many Requests`: rate limiting if
configured. - `500 Internal Server Error`: unexpected server error; do
not expose stack traces in production.

Example validation error:

``` json
{
  "completion_notes": [
    "This field is required when completing a work order."
  ]
}
```

Keep error shapes consistent and document any custom exception handler.

## 9. API implementation conventions

-   Use `/api/v1/` for all application endpoints.
-   Use serializers for input validation and output representation.
-   Use explicit permission classes.
-   Scope all tenant querysets.
-   Derive organization from the authenticated user.
-   Validate organization consistency for every related foreign key.
-   Use explicit action endpoints for state transitions.
-   Use transactions for multi-record operations.
-   Paginate list endpoints.
-   Document request/response schemas in OpenAPI.
-   Add tests for successful requests, validation errors, permissions,
    and cross-organization access.

## 10. Swagger / OpenAPI

Use `drf-spectacular` to expose: - OpenAPI schema. - Swagger UI. - ReDoc
(optional).

The API documentation should describe authentication, role access,
filters, pagination, request examples, response schemas, and error
cases. Keep the schema in sync with actual endpoint behavior.
