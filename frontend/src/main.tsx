import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import {
  createBrowserRouter,
  Navigate,
  RouterProvider,
  type RouteObject,
} from "react-router-dom";
import "./index.css";
import { session } from "./lib/api";
import Login from "./pages/Login";
import Patients from "./pages/Patients";
import PatientDetail from "./pages/PatientDetail";

// Apply the persisted theme before first paint to avoid a flash.
if (localStorage.getItem("tejasri.theme") === "dark") {
  document.documentElement.classList.add("dark");
}

function Protected({ children }: { children: React.ReactElement }) {
  return session.token ? children : <Navigate to="/login" replace />;
}

const routes: RouteObject[] = [
  { path: "/login", element: <Login /> },
  {
    path: "/patients",
    element: (
      <Protected>
        <Patients />
      </Protected>
    ),
  },
  {
    path: "/patients/:patientId",
    element: (
      <Protected>
        <PatientDetail />
      </Protected>
    ),
  },
  { path: "*", element: <Navigate to="/patients" replace /> },
];

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <RouterProvider router={createBrowserRouter(routes)} />
  </StrictMode>,
);
