import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { useForm, type FieldPath } from "react-hook-form";
import { Link, Navigate, useNavigate, useParams } from "react-router-dom";
import { z } from "zod";

import {
  createCategory,
  createEquipment,
  getEquipment,
  listCategories,
  updateEquipment,
} from "../../api/equipment";
import { isNotFound, parseApiError } from "../../api/errors";
import { buttonPrimary, buttonSecondary, inputClass } from "../../components/styles";
import { ErrorBox, FormField, Spinner } from "../../components/ui";
import { EDITABLE_STATUSES, STATUS_LABELS } from "../../constants";
import type { Equipment, EquipmentPayload } from "../../types";

const schema = z
  .object({
    equipment_code: z.string().trim().min(1, "Code is required").max(50, "Max 50 characters"),
    name: z.string().trim().min(1, "Name is required").max(160, "Max 160 characters"),
    category: z.string(), // "" = tanpa kategori
    status: z.enum(EDITABLE_STATUSES),
    location: z.string().trim().min(1, "Location is required").max(160, "Max 160 characters"),
    manufacturer: z.string().trim().max(120, "Max 120 characters"),
    model_number: z.string().trim().max(120, "Max 120 characters"),
    serial_number: z.string().trim().max(120, "Max 120 characters"),
    purchase_date: z.string(), // "" atau YYYY-MM-DD
    installation_date: z.string(),
    description: z.string().trim(),
  })
  .refine((v) => !v.purchase_date || !v.installation_date || v.installation_date >= v.purchase_date, {
    path: ["installation_date"],
    message: "Installation date cannot be before the purchase date",
  });

type FormValues = z.infer<typeof schema>;

const EMPTY_VALUES: FormValues = {
  equipment_code: "",
  name: "",
  category: "",
  status: "OPERATIONAL",
  location: "",
  manufacturer: "",
  model_number: "",
  serial_number: "",
  purchase_date: "",
  installation_date: "",
  description: "",
};

function toFormValues(item: Equipment): FormValues {
  return {
    equipment_code: item.equipment_code,
    name: item.name,
    category: item.category ?? "",
    // RETIRED tidak bisa diedit, jadi di sini status pasti salah satu dari tiga pilihan
    status: item.status as FormValues["status"],
    location: item.location,
    manufacturer: item.manufacturer,
    model_number: item.model_number,
    serial_number: item.serial_number,
    purchase_date: item.purchase_date ?? "",
    installation_date: item.installation_date ?? "",
    description: item.description,
  };
}

/** Ubah nilai form (semua string) menjadi payload API (tanggal/kategori kosong menjadi null). */
function toPayload(values: FormValues): EquipmentPayload {
  return {
    equipment_code: values.equipment_code,
    name: values.name,
    category: values.category || null,
    status: values.status,
    location: values.location,
    manufacturer: values.manufacturer,
    model_number: values.model_number,
    serial_number: values.serial_number,
    description: values.description,
    purchase_date: values.purchase_date || null,
    installation_date: values.installation_date || null,
  };
}

/** Tambah kategori baru tanpa meninggalkan form. */
function NewCategory({ onCreated }: { onCreated: (id: string) => void }) {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");

  const create = useMutation({
    mutationFn: () => createCategory(name.trim()),
    onSuccess: async (category) => {
      // Catat ID SEBELUM daftar di-refresh, agar form tahu kategori mana yang harus dipilih
      onCreated(category.id);
      await queryClient.invalidateQueries({ queryKey: ["equipment-categories"] });
      setName("");
      setOpen(false);
    },
  });

  if (!open) {
    return (
      <button type="button" className="mt-1 text-xs font-medium text-blue-600 hover:underline" onClick={() => setOpen(true)}>
        + New category
      </button>
    );
  }

  return (
    <div className="mt-2 space-y-1">
      <div className="flex gap-2">
        <input
          aria-label="New category name"
          className={inputClass}
          placeholder="Category name"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <button type="button" className={buttonSecondary} disabled={!name.trim() || create.isPending} onClick={() => create.mutate()}>
          Add
        </button>
        <button type="button" className={buttonSecondary} onClick={() => setOpen(false)}>
          Cancel
        </button>
      </div>
      {create.isError && <p className="text-xs text-red-600">{parseApiError(create.error).fieldErrors.name ?? parseApiError(create.error).message}</p>}
    </div>
  );
}

function EquipmentFormBody({ equipment }: { equipment?: Equipment }) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [serverError, setServerError] = useState("");
  const isEdit = Boolean(equipment);

  const categories = useQuery({ queryKey: ["equipment-categories"], queryFn: listCategories });
  // ID kategori yang baru dibuat; dipilih otomatis setelah opsinya benar-benar tampil
  const pendingCategoryId = useRef<string | null>(null);

  const {
    register,
    handleSubmit,
    setError,
    setValue,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: equipment ? toFormValues(equipment) : EMPTY_VALUES,
  });

  // Menunggu daftar kategori ter-render sebelum memilihnya. Jika setValue dipanggil
  // sebelum <option> baru ada di DOM, pilihan akan jatuh kembali ke "No category".
  useEffect(() => {
    const pending = pendingCategoryId.current;
    if (pending && categories.data?.some((category) => category.id === pending)) {
      setValue("category", pending, { shouldDirty: true });
      pendingCategoryId.current = null;
    }
  }, [categories.data, setValue]);

  const save = useMutation({
    mutationFn: (values: FormValues) => {
      const payload = toPayload(values);
      return equipment ? updateEquipment(equipment.id, payload) : createEquipment(payload);
    },
    onSuccess: async (saved) => {
      await queryClient.invalidateQueries({ queryKey: ["equipment"] });
      navigate(`/equipment/${saved.id}`);
    },
    onError: (error) => {
      const { message, fieldErrors } = parseApiError(error);
      let handled = false;
      // Tampilkan error dari server di bawah field yang bersangkutan
      for (const [field, text] of Object.entries(fieldErrors)) {
        if (field in EMPTY_VALUES) {
          setError(field as FieldPath<FormValues>, { message: text });
          handled = true;
        }
      }
      // Error per field sudah tampil di bawah inputnya; sisanya (403, 409, jaringan) tampil di atas form
      setServerError(handled ? "" : message);
    },
  });

  function onSubmit(values: FormValues) {
    setServerError("");
    save.mutate(values);
  }

  const field = (name: FieldPath<FormValues>) => ({ ...register(name), id: name });

  return (
    <div className="mx-auto max-w-3xl">
      <Link to={equipment ? `/equipment/${equipment.id}` : "/equipment"} className="text-sm text-blue-600 hover:underline">
        ← Back
      </Link>
      <h1 className="mb-6 mt-2 text-2xl font-bold">{isEdit ? `Edit ${equipment?.equipment_code}` : "Add equipment"}</h1>

      <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-5 rounded-lg border border-slate-200 bg-white p-6">
        {serverError && <ErrorBox message={serverError} />}

        <div className="grid gap-5 sm:grid-cols-2">
          <FormField label="Equipment code" htmlFor="equipment_code" required error={errors.equipment_code?.message}>
            <input className={inputClass} placeholder="CNC-001" {...field("equipment_code")} />
          </FormField>
          <FormField label="Name" htmlFor="name" required error={errors.name?.message}>
            <input className={inputClass} {...field("name")} />
          </FormField>

          <div>
            <FormField label="Category" htmlFor="category" error={errors.category?.message}>
              <select className={inputClass} {...field("category")}>
                <option value="">No category</option>
                {categories.data?.map((category) => (
                  <option key={category.id} value={category.id}>
                    {category.name}
                  </option>
                ))}
              </select>
            </FormField>
            <NewCategory onCreated={(id) => (pendingCategoryId.current = id)} />
          </div>
          <FormField label="Status" htmlFor="status" error={errors.status?.message}>
            <select className={inputClass} {...field("status")}>
              {EDITABLE_STATUSES.map((status) => (
                <option key={status} value={status}>
                  {STATUS_LABELS[status]}
                </option>
              ))}
            </select>
          </FormField>

          <FormField label="Location" htmlFor="location" required error={errors.location?.message}>
            <input className={inputClass} {...field("location")} />
          </FormField>
          <FormField label="Manufacturer" htmlFor="manufacturer" error={errors.manufacturer?.message}>
            <input className={inputClass} {...field("manufacturer")} />
          </FormField>
          <FormField label="Model number" htmlFor="model_number" error={errors.model_number?.message}>
            <input className={inputClass} {...field("model_number")} />
          </FormField>
          <FormField label="Serial number" htmlFor="serial_number" error={errors.serial_number?.message}>
            <input className={inputClass} {...field("serial_number")} />
          </FormField>
          <FormField label="Purchase date" htmlFor="purchase_date" error={errors.purchase_date?.message}>
            <input type="date" className={inputClass} {...field("purchase_date")} />
          </FormField>
          <FormField label="Installation date" htmlFor="installation_date" error={errors.installation_date?.message}>
            <input type="date" className={inputClass} {...field("installation_date")} />
          </FormField>
        </div>

        <FormField label="Description" htmlFor="description" error={errors.description?.message}>
          <textarea rows={3} className={inputClass} {...field("description")} />
        </FormField>

        <div className="flex justify-end gap-2">
          <Link to={equipment ? `/equipment/${equipment.id}` : "/equipment"} className={buttonSecondary}>
            Cancel
          </Link>
          <button type="submit" className={buttonPrimary} disabled={save.isPending}>
            {save.isPending ? "Saving..." : isEdit ? "Save changes" : "Create equipment"}
          </button>
        </div>
      </form>
    </div>
  );
}

/** Halaman create (/equipment/new) dan edit (/equipment/:id/edit) memakai komponen ini. */
export default function EquipmentForm() {
  const { id } = useParams();

  const equipment = useQuery({
    queryKey: ["equipment", "detail", id],
    queryFn: () => getEquipment(id as string),
    enabled: Boolean(id),
    retry: false,
  });

  if (!id) return <EquipmentFormBody />; // mode create

  if (equipment.isPending) return <Spinner />;
  if (equipment.isError) {
    return isNotFound(equipment.error) ? (
      <Navigate to="/equipment" replace />
    ) : (
      <ErrorBox message={parseApiError(equipment.error).message} onRetry={() => equipment.refetch()} />
    );
  }
  // Equipment yang sudah retired tidak boleh diedit
  if (equipment.data.retired_at) return <Navigate to={`/equipment/${id}`} replace />;

  // `key` memastikan form dibuat ulang jika data berganti
  return <EquipmentFormBody key={equipment.data.id} equipment={equipment.data} />;
}