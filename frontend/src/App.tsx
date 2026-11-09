import { Route, Routes } from "react-router-dom";

import Layout from "./components/Layout";
import { ProtectedRoute, RoleRoute } from "./components/RouteGuards";
import Dashboard from "./pages/Dashboard";
import EquipmentDetail from "./pages/equipment/EquipmentDetail";
import EquipmentForm from "./pages/equipment/EquipmentForm";
import EquipmentList from "./pages/equipment/EquipmentList";
import Login from "./pages/Login";
import NotFound from "./pages/NotFound";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />

      {/* Semua yang di bawah ini butuh login */}
      <Route element={<ProtectedRoute />}>
        <Route element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="equipment" element={<EquipmentList />} />

          {/* Hanya Admin dan Manager (UI saja; backend tetap menegakkan izin) */}
          <Route element={<RoleRoute allow={["ADMIN", "MANAGER"]} />}>
            <Route path="equipment/new" element={<EquipmentForm />} />
            <Route path="equipment/:id/edit" element={<EquipmentForm />} />
          </Route>

          <Route path="equipment/:id" element={<EquipmentDetail />} />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Route>
    </Routes>
  );
}