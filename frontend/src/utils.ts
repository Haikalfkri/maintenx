export function formatDate(value: string | null): string {
    if (!value) return "-";
    // Tanggal murni (YYYY-MM-DD) ditampilkan apa adanya agar tidak bergeser karena timezone
    if (/^\d{4}-\d{2}-\d{2}$/.test(value)) return value;
    return new Date(value).toLocaleDateString();
}

export function formatDateTime(value: string | null): string {
    if (!value) return "-";
    return new Date(value).toLocaleString();
}

export function fullName(user: { first_name: string; last_name: string; email: string }): string {
  return `${user.first_name} ${user.last_name}`.trim() || user.email;
}