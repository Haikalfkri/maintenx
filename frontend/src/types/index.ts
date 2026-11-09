export type Role = "ADMIN" | "MANAGER" | "TECHNICIAN"

export type EquipmentStatus =
  | "OPERATIONAL"
  | "UNDER_MAINTENANCE"
  | "OUT_OF_SERVICE"
  | "RETIRED";
  
export interface Organization {
    id: string;
    name: string;
    timezone: string;
}

export interface CurrentUser {
    id: string;
    email: string;
    first_name: string;
    last_name: string;
    role: Role;
    organization: Organization;
}

export interface Tokens {
    access: string;
    refresh: string;
}

// response list dari backend
export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface EquipmentCategory {
    id: string;
    name: string;
    description: string;
    created_at: string;
}

export interface Equipment {
  id: string;
  equipment_code: string;
  name: string;
  description: string;
  category: string | null;
  category_name: string | null;
  manufacturer: string;
  model_number: string;
  serial_number: string;
  location: string;
  purchase_date: string | null;
  installation_date: string | null;
  status: EquipmentStatus;
  created_at: string;
  updated_at: string;
  retired_at: string | null;
}

// data yang dikirim ke backend saat create/update
export interface EquipmentPayload {
  equipment_code: string;
  name: string;
  description: string;
  category: string | null;
  manufacturer: string;
  model_number: string;
  serial_number: string;
  location: string;
  purchase_date: string | null;
  installation_date: string | null;
  status: Exclude<EquipmentStatus, "RETIRED">;
}

export interface HistoryEvent {
  id: string;
  action: string;
  actor: string | null;
  actor_name: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
}