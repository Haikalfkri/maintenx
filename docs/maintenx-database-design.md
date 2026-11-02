# MaintenX --- Database Design

## 1. Purpose and conventions

This document defines the initial PostgreSQL relational model for the
MaintenX MVP.

Conventions: - Primary keys: UUID recommended for public-facing
entities; integer IDs are acceptable if chosen consistently. -
Timestamps: timezone-aware `created_at` and `updated_at` where
applicable. - Store timestamps in UTC; convert to the organization's
configured timezone for business-date calculations and display. - Use
`PROTECT` or soft-retirement patterns for important operational history
rather than cascading deletion. - Every tenant-owned table includes an
`organization_id` foreign key. - Use database constraints for uniqueness
and basic integrity; enforce cross-table tenant consistency in services
and tests.

## 2. Entity relationship diagram

``` mermaid
erDiagram
    ORGANIZATION ||--o{ USER : has
    ORGANIZATION ||--o{ EQUIPMENT_CATEGORY : defines
    ORGANIZATION ||--o{ EQUIPMENT : owns
    EQUIPMENT_CATEGORY ||--o{ EQUIPMENT : classifies
    EQUIPMENT ||--o{ MAINTENANCE_PLAN : follows
    ORGANIZATION ||--o{ MAINTENANCE_PLAN : owns
    EQUIPMENT ||--o{ WORK_ORDER : receives
    ORGANIZATION ||--o{ WORK_ORDER : owns
    USER ||--o{ WORK_ORDER : assigned_to
    USER ||--o{ WORK_ORDER : reported_by
    MAINTENANCE_PLAN ||--o{ WORK_ORDER : generates
    WORK_ORDER ||--o{ WORK_ORDER_HISTORY : records
    USER ||--o{ WORK_ORDER_HISTORY : performs
    EQUIPMENT ||--o{ DOWNTIME_RECORD : experiences
    WORK_ORDER ||--o{ DOWNTIME_RECORD : relates_to
    USER ||--o{ DOWNTIME_RECORD : records
    ORGANIZATION ||--o{ AUDIT_LOG : owns
    USER ||--o{ AUDIT_LOG : acts
```

## 3. Tables and fields

### 3.1 Organization

  ---------------------------------------------------------------------------------
  Field                             Type                    Rules
  --------------------------------- ----------------------- -----------------------
  id                                UUID / bigint           Primary key

  name                              varchar(160)            Required

  slug                              varchar(100)            Unique

  timezone                          varchar(64)             Default `Asia/Jakarta`
                                                            for demo

  assumed_operating_hours_per_day   decimal(5,2)            Configurable, positive

  is_active                         boolean                 Default true

  created_at                        timestamptz             Required

  updated_at                        timestamptz             Required
  ---------------------------------------------------------------------------------

### 3.2 User

Use a custom Django user model before the first migration. A practical
MVP design uses one organization per user.

  Field             Type                   Rules
  ----------------- ---------------------- -------------------------------------------------
  id                UUID / bigint          Primary key
  email             varchar                Unique login identifier
  password          Django password hash   Never store plaintext
  first_name        varchar                Optional/required by product decision
  last_name         varchar                Optional
  organization_id   FK Organization        Required for application users
  role              varchar                `ADMIN`, `MANAGER`, `TECHNICIAN`
  is_active         boolean                Default true
  is_staff          boolean                Django admin access, separate from product role
  is_superuser      boolean                Restricted platform-level access
  created_at        timestamptz            Required
  updated_at        timestamptz            Required

Do not equate Django `is_staff` with the MaintenX organization Admin
role.

### 3.3 EquipmentCategory

  Field             Type              Rules
  ----------------- ----------------- -------------
  id                UUID / bigint     Primary key
  organization_id   FK Organization   Required
  name              varchar(100)      Required
  description       text              Optional
  created_at        timestamptz       Required

Constraint: unique `(organization_id, name)`.

### 3.4 Equipment

  Field               Type                   Rules
  ------------------- ---------------------- -----------------------
  id                  UUID / bigint          Primary key
  organization_id     FK Organization        Required
  category_id         FK EquipmentCategory   Optional
  equipment_code      varchar(50)            Required
  name                varchar(160)           Required
  description         text                   Optional
  manufacturer        varchar(120)           Optional
  model_number        varchar(120)           Optional
  serial_number       varchar(120)           Optional
  location            varchar(160)           Required
  purchase_date       date                   Optional
  installation_date   date                   Optional
  status              varchar(32)            Equipment status enum
  created_at          timestamptz            Required
  updated_at          timestamptz            Required
  retired_at          timestamptz            Optional

Constraint: unique `(organization_id, equipment_code)`. Add indexes for
`(organization_id, status)`, `(organization_id, location)`, and category
where useful.

### 3.5 MaintenancePlan

  Field                        Type               Rules
  ---------------------------- ------------------ ------------------------------
  id                           UUID / bigint      Primary key
  organization_id              FK Organization    Required
  equipment_id                 FK Equipment       Required
  title                        varchar(160)       Required
  description                  text               Optional
  frequency                    varchar(16)        `DAILY`, `WEEKLY`, `MONTHLY`
  interval_value               positive integer   MVP default 1
  start_date                   date               Required
  next_due_date                date               Required
  estimated_duration_minutes   positive integer   Optional
  default_technician_id        FK User            Optional
  is_active                    boolean            Default true
  created_at                   timestamptz        Required
  updated_at                   timestamptz        Required

Validate that equipment and default technician belong to the same
organization. Index `(organization_id, is_active, next_due_date)`.

For robust idempotency, add a `MaintenanceOccurrence` table or
equivalent unique occurrence key: - `maintenance_plan_id` -
`scheduled_due_date` - `generated_work_order_id` - `created_at`

Constraint: unique `(maintenance_plan_id, scheduled_due_date)`. This is
safer than relying only on application-level duplicate checks.

### 3.6 WorkOrder

  Field                    Type                 Rules
  ------------------------ -------------------- -------------------------------------
  id                       UUID / bigint        Primary key
  organization_id          FK Organization      Required
  work_order_number        varchar(40)          Required
  equipment_id             FK Equipment         Required
  maintenance_plan_id      FK MaintenancePlan   Optional
  title                    varchar(160)         Required
  description              text                 Optional
  work_order_type          varchar(20)          `CORRECTIVE`, `PREVENTIVE`
  priority                 varchar(16)          `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`
  status                   varchar(20)          Workflow enum
  assigned_technician_id   FK User              Optional
  reported_by_id           FK User              Required
  due_date                 date                 Optional
  started_at               timestamptz          Optional
  completed_at             timestamptz          Optional
  completion_notes         text                 Required on completion
  actual_labor_minutes     positive integer     Optional
  created_at               timestamptz          Required
  updated_at               timestamptz          Required

Constraint: unique `(organization_id, work_order_number)`. Index
`(organization_id, status)`,
`(organization_id, assigned_technician_id, status)`, and
`(organization_id, created_at)`.

Validate all related records belong to the same organization. Prevent
arbitrary client changes to status; use dedicated workflow actions.

### 3.7 WorkOrderHistory

  Field             Type              Rules
  ----------------- ----------------- -------------------------
  id                UUID / bigint     Primary key
  organization_id   FK Organization   Required
  work_order_id     FK WorkOrder      Required
  actor_id          FK User           Required
  event_type        varchar(40)       Required
  from_status       varchar(20)       Optional
  to_status         varchar(20)       Optional
  note              text              Optional
  metadata          JSONB             Optional, non-sensitive
  created_at        timestamptz       Required

Use this table for a user-visible work-order timeline and auditability
of state transitions.

### 3.8 DowntimeRecord

  -----------------------------------------------------------------------
  Field                   Type                    Rules
  ----------------------- ----------------------- -----------------------
  id                      UUID / bigint           Primary key

  organization_id         FK Organization         Required

  equipment_id            FK Equipment            Required

  work_order_id           FK WorkOrder            Optional

  recorded_by_id          FK User                 Required

  reason                  varchar(20)             `MECHANICAL`,
                                                  `ELECTRICAL`,
                                                  `OPERATOR`, `OTHER`

  description             text                    Optional

  started_at              timestamptz             Required

  ended_at                timestamptz             Null while still down

  created_at              timestamptz             Required

  updated_at              timestamptz             Required
  -----------------------------------------------------------------------

Indexes: `(organization_id, started_at)`,
`(organization_id, equipment_id, started_at)`. Validate
`ended_at >= started_at`. Prevent overlapping open downtime for the same
equipment; use a transaction and, if practical, a PostgreSQL partial
unique constraint for one open record per equipment. More complex
overlap prevention may require exclusion constraints or service-level
locking.

Duration should be calculated from timestamps, not stored as a
client-submitted value.

### 3.9 AuditLog

  Field             Type              Rules
  ----------------- ----------------- ----------------------------
  id                UUID / bigint     Primary key
  organization_id   FK Organization   Required
  actor_id          FK User           Optional for system events
  action            varchar(60)       Required
  entity_type       varchar(80)       Required
  entity_id         varchar(64)       Required
  metadata          JSONB             Optional
  created_at        timestamptz       Required

Do not put passwords, tokens, or sensitive authentication payloads in
metadata.

## 4. Relationships and deletion policy

-   Organization → tenant records: protect against accidental deletion;
    organizations should be deactivated.
-   Equipment → maintenance plans/work orders/downtime: protect
    historical records; retire equipment instead.
-   Maintenance plan → generated work orders: preserve plan reference or
    retain occurrence history.
-   User → historical actions: do not cascade-delete history; deactivate
    users instead.
-   Work order → history: cascade may be acceptable only if work orders
    are truly deletable, but the recommended policy is to retain
    operational history and cancel rather than delete.

## 5. Enums

  -----------------------------------------------------------------------
  Enum                                Values
  ----------------------------------- -----------------------------------
  User role                           `ADMIN`, `MANAGER`, `TECHNICIAN`

  Equipment status                    `OPERATIONAL`, `UNDER_MAINTENANCE`,
                                      `OUT_OF_SERVICE`, `RETIRED`

  Maintenance frequency               `DAILY`, `WEEKLY`, `MONTHLY`

  Work-order type                     `CORRECTIVE`, `PREVENTIVE`

  Work-order priority                 `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`

  Work-order status                   `OPEN`, `ASSIGNED`, `IN_PROGRESS`,
                                      `COMPLETED`, `CANCELLED`

  Downtime reason                     `MECHANICAL`, `ELECTRICAL`,
                                      `OPERATOR`, `OTHER`
  -----------------------------------------------------------------------

## 6. Data integrity rules

1.  Every tenant-owned record has an organization.
2.  Related tenant-owned records must share the same organization.
3.  Equipment codes and work-order numbers are unique within an
    organization.
4.  A retired equipment item cannot receive a new plan or work order.
5.  A technician assignment must reference an active technician in the
    same organization.
6.  Work-order transitions must follow the defined state machine.
7.  Completion requires notes and valid timestamps.
8.  Downtime end must be after or equal to its start.
9.  A piece of equipment cannot have multiple simultaneously open
    downtime records.
10. One maintenance plan occurrence can generate at most one work order.

## 7. KPI calculation data requirements

-   MTTR requires completed corrective work orders with valid
    `started_at` and `completed_at`.
-   MTBF requires breakdown counts and a documented assumed
    operating-hours value; it is an estimate, not sensor-derived truth.
-   Downtime requires breakdown start/end timestamps; active incidents
    use the current time for elapsed duration.
-   Preventive completion rate requires preventive work orders and a
    defined reporting period.

Return sample counts with averages. Return null/no-data rather than
misleading zero or infinity when a metric cannot be calculated.

## 8. Suggested indexes

Start with: - Foreign keys (Django/PostgreSQL generally indexes FK
columns). - Organization + status for equipment and work orders. -
Organization + due date for maintenance plans. - Organization + assigned
technician + status for technician work queues. - Organization +
timestamp for downtime and audit records. - Unique constraints for
equipment code, work-order number, and maintenance occurrence.

Use `EXPLAIN ANALYZE` only when there is a query worth optimizing; do
not add indexes indiscriminately.

## 9. Migration and seed-data order

1.  Organization and custom User.
2.  EquipmentCategory and Equipment.
3.  MaintenancePlan and MaintenanceOccurrence.
4.  WorkOrder and WorkOrderHistory.
5.  DowntimeRecord.
6.  AuditLog.
7.  Add constraints and indexes.
8.  Create a management command to seed fictional demo organizations,
    users, equipment, plans, work orders, and downtime records.
