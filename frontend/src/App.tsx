import { Navigate, Outlet, Route, Routes } from "react-router-dom";
import { Layout } from "@/components/Layout";
import { useAuth } from "@/lib/auth";
import type { Role } from "@/lib/types";
import Activate from "@/pages/Activate";
import Cards from "@/pages/Cards";
import Dashboard from "@/pages/Dashboard";
import Login from "@/pages/Login";
import { ForgotPassword, ResetPassword } from "@/pages/PasswordReset";
import Profile from "@/pages/Profile";
import Register from "@/pages/Register";
import System from "@/pages/System";
import Transactions from "@/pages/Transactions";
import Transfer from "@/pages/Transfer";
import Withdraw from "@/pages/Withdraw";
import Customers from "@/pages/staff/Customers";
import Deposit from "@/pages/staff/Deposit";
import Kyc from "@/pages/staff/Kyc";
import StaffHome from "@/pages/staff/StaffHome";

function Splash() { return <div className="flex min-h-screen items-center justify-center text-sm text-muted-foreground">Loading…</div>; }

function RequireAuth() { const { user, loading } = useAuth(); if (loading) return <Splash />; return user ? <Layout /> : <Navigate to="/login" replace />; }
function GuestOnly() { const { user, loading } = useAuth(); if (loading) return <Splash />; return user ? <Navigate to="/" replace /> : <Outlet />; }
function RequireRole({ role }: { role: Role }) { const { hasRole } = useAuth(); return hasRole(role) ? <Outlet /> : <Navigate to="/" replace />; }
function RequireCustomer() { const { isStaff } = useAuth(); return isStaff ? <Navigate to="/" replace /> : <Outlet />; }
function Home() { const { isStaff } = useAuth(); return isStaff ? <StaffHome /> : <Dashboard />; }

export default function App() {
  return (
    <Routes>
      <Route element={<GuestOnly />}>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/forgot-password" element={<ForgotPassword />} />
      </Route>
      {/* e-mail links work whether or not you are signed in */}
      <Route path="/activate/:uid/:token" element={<Activate />} />
      <Route path="/password-reset/:uid/:token" element={<ResetPassword />} />

      <Route element={<RequireAuth />}>
        <Route index element={<Home />} />
        <Route path="profile" element={<Profile />} />
        <Route element={<RequireCustomer />}>
          <Route path="transfer" element={<Transfer />} />
          <Route path="withdraw" element={<Withdraw />} />
          <Route path="transactions" element={<Transactions />} />
          <Route path="cards" element={<Cards />} />
        </Route>
        <Route element={<RequireRole role="teller" />}><Route path="staff/deposit" element={<Deposit />} /></Route>
        <Route element={<RequireRole role="account_executive" />}><Route path="staff/kyc" element={<Kyc />} /></Route>
        <Route element={<RequireRole role="branch_manager" />}>
          <Route path="staff/customers" element={<Customers />} />
          <Route path="system" element={<System />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
