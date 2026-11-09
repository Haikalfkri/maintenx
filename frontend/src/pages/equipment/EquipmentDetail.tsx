import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";
import { Link, useParams } from "react-router-dom";

import { getEquipment, getEquipmentHistory, retireEquipment } from "../../api/equipment";
import { isNotFound, parseApiError } from "../../api/errors";
import { buttonDanger, buttonSecondary } from "../../components/styles";
import { ErrorBox, Pagination, Spinner, StatusBadge } from "../../components/ui";
import { useAuth } from "../../hooks/auth-context";
import type { Equipment, HistoryEvent } from "../../types";
import { formatDate, formatDateTime } from "../../utils";

const FIELD_LABELS: Record<string, string> = {
  equipment_code: "code",
  name: "name",
  description: "description",
  category_id: "category",
  manufacturer: "manufacturer",
  model_number: "model number",
  serial_number: "serial number",
  location: "location",
  purchase_date: "purchase date",
  installation_date: "installation date",
  status: "status",
};

/** Ubah satu catatan audit menjadi kalimat yang mudah dibaca. */
function describeEvent(event: HistoryEvent): string {
  switch (event.action) {
    case "equipment.created":
      return "Equipment created";
    case "equipment.retired":
      return "Equipment retired";
    case "equipment.updated": {
      const changes = (event.metadata.changes ?? {}) as Record<string, { from: unknown; to: unknown }>;
      const parts = Object.entries(changes).map(([field, change]) => {
        const label = FIELD_LABELS[field] ?? field;
        // Kategori disimpan sebagai ID, jadi tidak ditampilkan nilainya
        if (field === "category_id") return `${label} changed`;
        return `${label}: "${String(change.from ?? "")}" → "${String(change.to ?? "")}"`;
      });
      return parts.length > 0 ? `Updated ${parts.join("; ")}` : "Equipment updated";
    }
    default:
      return event.action;
  }
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-slate-500">{label}</dt>
      <dd className="mt-0.5 text-sm text-slate-900">{children || "-"}</dd>
    </div>
  );
}

function History({ id }: { id: string }) {
  const [page, setPage] = useState(1);
  const history = useQuery({
    queryKey: ["equipment", "history", id, page],
    queryFn: () => getEquipmentHistory(id, page),
  });

  return (
    <section className="rounded-lg border border-slate-200 bg-white">
      <h2 className="border-b border-slate-200 px-4 py-3 font-semibold">History</h2>
      {history.isPending ? (
        <Spinner />
      ) : history.isError ? (
        <div className="p-4">
          <ErrorBox message={parseApiError(history.error).message} onRetry={() => history.refetch()} />
        </div>
      ) : history.data.results.length === 0 ? (
        <p className="p-4 text-sm text-slate-500">No recorded events yet.</p>
      ) : (
        <>
          <ul className="divide-y divide-slate-100">
            {history.data.results.map((event) => (
              <li key={event.id} className="px-4 py-3 text-sm">
                <p>{describeEvent(event)}</p>
                <p className="mt-0.5 text-xs text-slate-500">
                  {formatDateTime(event.created_at)} · {event.actor_name ?? "System"}
                </p>
              </li>
            ))}
          </ul>
          <Pagination page={page} count={history.data.count} onChange={setPage} />
        </>
      )}
    </section>
  );
}

export default function EquipmentDetail() {
  const { id = "" } = useParams();
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const canManage = user?.role === "ADMIN" || user?.role === "MANAGER";

  const equipment = useQuery({
    queryKey: ["equipment", "detail", id],
    queryFn: () => getEquipment(id),
    retry: false,
  });

  const retire = useMutation({
    mutationFn: () => retireEquipment(id),
    // Semua query "equipment" (list, detail, history) diambil ulang
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["equipment"] }),
  });

  function handleRetire(item: Equipment) {
    const confirmed = window.confirm(
      `Retire ${item.equipment_code}? Retired equipment can no longer be edited or receive new work.`,
    );
    if (confirmed) retire.mutate();
  }

  if (equipment.isPending) return <Spinner />;
  if (equipment.isError) {
    return isNotFound(equipment.error) ? (
      <div className="py-12 text-center">
        <p className="font-medium">Equipment not found</p>
        <Link to="/equipment" className="mt-2 inline-block text-sm text-blue-600 hover:underline">
          Back to equipment list
        </Link>
      </div>
    ) : (
      <ErrorBox message={parseApiError(equipment.error).message} onRetry={() => equipment.refetch()} />
    );
  }

  const item = equipment.data;

  return (
    <div className="space-y-6">
      <Link to="/equipment" className="text-sm text-blue-600 hover:underline">
        ← Equipment
      </Link>

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">
            {item.equipment_code} <span className="font-normal text-slate-500">· {item.name}</span>
          </h1>
          <div className="mt-2">
            <StatusBadge status={item.status} />
          </div>
        </div>

        {canManage && !item.retired_at && (
          <div className="flex gap-2">
            <Link to={`/equipment/${item.id}/edit`} className={buttonSecondary}>
              Edit
            </Link>
            <button type="button" className={buttonDanger} disabled={retire.isPending} onClick={() => handleRetire(item)}>
              {retire.isPending ? "Retiring..." : "Retire"}
            </button>
          </div>
        )}
      </div>

      {retire.isError && <ErrorBox message={parseApiError(retire.error).message} />}

      {item.retired_at && (
        <div className="rounded-md border border-slate-300 bg-slate-100 p-3 text-sm text-slate-700">
          This equipment was retired on {formatDateTime(item.retired_at)} and can no longer be edited.
        </div>
      )}

      <section className="rounded-lg border border-slate-200 bg-white p-4">
        <dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <Field label="Category">{item.category_name}</Field>
          <Field label="Location">{item.location}</Field>
          <Field label="Manufacturer">{item.manufacturer}</Field>
          <Field label="Model number">{item.model_number}</Field>
          <Field label="Serial number">{item.serial_number}</Field>
          <Field label="Purchase date">{formatDate(item.purchase_date)}</Field>
          <Field label="Installation date">{formatDate(item.installation_date)}</Field>
          <Field label="Created">{formatDateTime(item.created_at)}</Field>
          <Field label="Last updated">{formatDateTime(item.updated_at)}</Field>
        </dl>
        {item.description && (
          <div className="mt-4 border-t border-slate-100 pt-4">
            <p className="text-xs uppercase tracking-wide text-slate-500">Description</p>
            <p className="mt-1 whitespace-pre-line text-sm">{item.description}</p>
          </div>
        )}
      </section>

      <History id={item.id} />
    </div>
  );
}