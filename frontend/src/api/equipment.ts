import type {
  Equipment,
  EquipmentCategory,
  EquipmentPayload,
  HistoryEvent,
  Paginated,
} from "../types";
import { api } from "./client";

export interface EquipmentListParams {
  page?: number;
  search?: string;
  status?: string;
  category?: string;
  location?: string;
}

function clean(params: object): Record<string, string | number> {
  return Object.fromEntries(
    Object.entries(params).filter(([, v]) => v !== "" && v !== undefined && v !== null),
  ) as Record<string, string | number>;
}

export async function listEquipment(params: EquipmentListParams): Promise<Paginated<Equipment>> {
  const { data } = await api.get<Paginated<Equipment>>("/equipment/", { params: clean(params) });
  return data;
}

export async function getEquipment(id: string): Promise<Equipment> {
  const { data } = await api.get<Equipment>(`/equipment/${id}/`);
  return data;
}

export async function createEquipment(payload: EquipmentPayload): Promise<Equipment> {
  const { data } = await api.post<Equipment>("/equipment/", payload);
  return data;
}

export async function updateEquipment(id: string, payload: EquipmentPayload): Promise<Equipment> {
  const { data } = await api.patch<Equipment>(`/equipment/${id}/`, payload);
  return data;
}

export async function retireEquipment(id: string): Promise<Equipment> {
  const { data } = await api.post<Equipment>(`/equipment/${id}/retire/`);
  return data;
}

export async function getEquipmentHistory(
  id: string,
  page: number,
): Promise<Paginated<HistoryEvent>> {
  const { data } = await api.get<Paginated<HistoryEvent>>(`/equipment/${id}/history/`, {
    params: { page },
  });
  return data;
}

export async function listCategories(): Promise<EquipmentCategory[]> {
  const { data } = await api.get<EquipmentCategory[]>("/equipment-categories/");
  return data;
}

export async function createCategory(name: string): Promise<EquipmentCategory> {
  const { data } = await api.post<EquipmentCategory>("/equipment-categories/", { name });
  return data;
}