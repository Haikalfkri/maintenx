import type { EquipmentStatus, Role } from "./types";

export const PAGE_SIZE = 20;

export const STATUS_LABELS: Record<EquipmentStatus, string> = {
    OPERATIONAL: "Operational",
    UNDER_MAINTENANCE: "Under maintenance",
    OUT_OF_SERVICE: "Out of service",
    RETIRED: "Retired",
};

export const EDITABLE_STATUSES = [
  "OPERATIONAL",
  "UNDER_MAINTENANCE",
  "OUT_OF_SERVICE",
] as const;

export const ROLE_LABELS: Record<Role, string> = {
  ADMIN: "Admin",
  MANAGER: "Manager",
  TECHNICIAN: "Technician",
};