import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";

import { listCategories, listEquipment } from "../../api/equipment";
import { parseApiError } from "../../api/errors";
import { buttonPrimary, inputClass } from "../../components/styles";
import { EmptyState, ErrorBox, Pagination, Spinner, StatusBadge } from "../../components/ui";
import { STATUS_LABELS } from "../../constants";
import { useAuth } from "../../hooks/auth-context";
import { useDebounce } from "../../hooks/useDebounce";
import type { EquipmentStatus } from "../../types";

interface Filters {
  search: string;
  status: string;
  category: string;
  location: string;
}

const EMPTY_FILTERS: Filters = { search: "", status: "", category: "", location: "" };

export default function EquipmentList() {
  const { user } = useAuth();
  const canManage = user?.role === "ADMIN" || user?.role === "MANAGER";

  const [filters, setFilters] = useState<Filters>(EMPTY_FILTERS);
  const [page, setPage] = useState(1);

  // Teks diketik bebas, tetapi request baru dikirim setelah berhenti mengetik
  const search = useDebounce(filters.search);
  const location = useDebounce(filters.location);

  const params = { page, search, location, status: filters.status, category: filters.category };

  const equipment = useQuery({
    queryKey: ["equipment", "list", params],
    queryFn: () => listEquipment(params),
    placeholderData: keepPreviousData, // tabel lama tetap tampil saat memuat halaman baru
  });
  const categories = useQuery({ queryKey: ["equipment-categories"], queryFn: listCategories });

  function updateFilter(patch: Partial<Filters>) {
    setFilters((current) => ({ ...current, ...patch }));
    setPage(1); // setiap filter berubah, kembali ke halaman pertama
  }

  const hasFilters = Object.values(filters).some((value) => value !== "");

  return (
    <div>
      <div className="mb-4 flex items-center justify-between gap-4">
        <h1 className="text-2xl font-bold">Equipment</h1>
        {canManage && (
          <Link to="/equipment/new" className={buttonPrimary}>
            Add equipment
          </Link>
        )}
      </div>

      <div className="mb-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <input
          type="search"
          placeholder="Search code, name, serial, location"
          aria-label="Search equipment"
          className={inputClass}
          value={filters.search}
          onChange={(e) => updateFilter({ search: e.target.value })}
        />
        <select
          aria-label="Filter by status"
          className={inputClass}
          value={filters.status}
          onChange={(e) => updateFilter({ status: e.target.value })}
        >
          <option value="">All statuses</option>
          {(Object.keys(STATUS_LABELS) as EquipmentStatus[]).map((status) => (
            <option key={status} value={status}>
              {STATUS_LABELS[status]}
            </option>
          ))}
        </select>
        <select
          aria-label="Filter by category"
          className={inputClass}
          value={filters.category}
          onChange={(e) => updateFilter({ category: e.target.value })}
        >
          <option value="">All categories</option>
          {categories.data?.map((category) => (
            <option key={category.id} value={category.id}>
              {category.name}
            </option>
          ))}
        </select>
        <input
          type="search"
          placeholder="Filter by location"
          aria-label="Filter by location"
          className={inputClass}
          value={filters.location}
          onChange={(e) => updateFilter({ location: e.target.value })}
        />
      </div>

      <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
        {equipment.isPending ? (
          <Spinner />
        ) : equipment.isError ? (
          <div className="p-4">
            <ErrorBox message={parseApiError(equipment.error).message} onRetry={() => equipment.refetch()} />
          </div>
        ) : equipment.data.results.length === 0 ? (
          hasFilters ? (
            <EmptyState
              title="No equipment matches your filters"
              description="Try a different search or clear the filters."
              action={
                <button type="button" className="text-sm font-medium text-blue-600 hover:underline" onClick={() => updateFilter(EMPTY_FILTERS)}>
                  Clear filters
                </button>
              }
            />
          ) : (
            <EmptyState
              title="No equipment yet"
              description={canManage ? "Add your first machine to get started." : "Nothing has been registered yet."}
              action={
                canManage && (
                  <Link to="/equipment/new" className={buttonPrimary}>
                    Add equipment
                  </Link>
                )
              }
            />
          )
        ) : (
          <>
            <div className={`overflow-x-auto ${equipment.isPlaceholderData ? "opacity-60" : ""}`}>
              <table className="min-w-full divide-y divide-slate-200 text-sm">
                <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
                  <tr>
                    <th className="px-4 py-3">Code</th>
                    <th className="px-4 py-3">Name</th>
                    <th className="px-4 py-3">Category</th>
                    <th className="px-4 py-3">Location</th>
                    <th className="px-4 py-3">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {equipment.data.results.map((item) => (
                    <tr key={item.id} className="hover:bg-slate-50">
                      <td className="whitespace-nowrap px-4 py-3 font-medium">
                        <Link to={`/equipment/${item.id}`} className="text-blue-700 hover:underline">
                          {item.equipment_code}
                        </Link>
                      </td>
                      <td className="px-4 py-3">{item.name}</td>
                      <td className="px-4 py-3 text-slate-600">{item.category_name ?? "-"}</td>
                      <td className="px-4 py-3 text-slate-600">{item.location}</td>
                      <td className="px-4 py-3">
                        <StatusBadge status={item.status} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination page={page} count={equipment.data.count} onChange={setPage} />
          </>
        )}
      </div>
    </div>
  );
}