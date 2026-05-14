import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { useEffect, useState } from "react";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import RouteForm from "./pages/RouteForm";
import RouteDetail from "./pages/RouteDetail";
import { api } from "./lib/api";

export default function App() {
  const [authed, setAuthed] = useState(false);
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    api.listRoutes().then(() => setAuthed(true)).catch(() => {}).finally(() => setChecking(false));
  }, []);

  if (checking) return null;

  if (!authed) {
    return <Login onLogin={() => setAuthed(true)} />;
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route
          path="/"
          element={<Dashboard onLogout={() => setAuthed(false)} />}
        />
        <Route path="/routes/new" element={<RouteForm />} />
        <Route path="/routes/:id/edit" element={<RouteForm />} />
        <Route path="/routes/:id" element={<RouteDetail />} />
        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </BrowserRouter>
  );
}
