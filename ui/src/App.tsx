import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { useState } from "react";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import RouteForm from "./pages/RouteForm";
import RouteDetail from "./pages/RouteDetail";

export default function App() {
  const [authed, setAuthed] = useState(false);

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
