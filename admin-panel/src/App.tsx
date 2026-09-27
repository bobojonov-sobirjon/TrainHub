import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider } from "./hooks/AuthProvider";
import { AdminLayout } from "./layouts/AdminLayout";
import { LoginPage } from "./pages/Login";
import { DashboardPage } from "./pages/Dashboard";
import { UsersPage } from "./pages/Users";
import { UserDetailPage } from "./pages/UserDetail";
import { ClientsPage } from "./pages/Clients";
import { ClientDetailPage } from "./pages/ClientDetail";
import { ProgramsPage } from "./pages/Programs";
import { ProgramDetailPage } from "./pages/ProgramDetail";
import { ExercisesPage } from "./pages/Exercises";
import { ExerciseDetailPage } from "./pages/ExerciseDetail";
import { PaymentsPage } from "./pages/Payments";
import { PaymentDetailPage, SubscriptionDetailPage } from "./pages/PaymentDetail";
import { FaqPage } from "./pages/Faq";
import { FaqDetailPage } from "./pages/FaqDetail";
import { TicketsPage } from "./pages/Tickets";
import { TicketDetailPage } from "./pages/TicketDetail";
import { LegalPage } from "./pages/Legal";
import { LegalDetailPage } from "./pages/LegalDetail";
import { ProtectedRoute } from "./router";

const queryClient = new QueryClient();

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route
              path="/"
              element={
                <ProtectedRoute>
                  <AdminLayout />
                </ProtectedRoute>
              }
            >
              <Route index element={<DashboardPage />} />
              <Route path="coaches" element={<UsersPage key="coaches" lockedRole="trainer" />} />
              <Route path="app-clients" element={<UsersPage key="app-clients" lockedRole="client" />} />
              <Route path="users" element={<UsersPage key="users" />} />
              <Route path="users/:id" element={<UserDetailPage />} />
              <Route path="clients" element={<ClientsPage />} />
              <Route path="clients/:id" element={<ClientDetailPage />} />
              <Route path="programs" element={<ProgramsPage />} />
              <Route path="programs/:id" element={<ProgramDetailPage />} />
              <Route path="exercises" element={<ExercisesPage />} />
              <Route path="exercises/:id" element={<ExerciseDetailPage />} />
              <Route path="payments" element={<PaymentsPage />} />
              <Route path="payments/:id" element={<PaymentDetailPage />} />
              <Route path="subscriptions/:id" element={<SubscriptionDetailPage />} />
              <Route path="faq" element={<FaqPage />} />
              <Route path="faq/:id" element={<FaqDetailPage />} />
              <Route path="tickets" element={<TicketsPage />} />
              <Route path="tickets/:id" element={<TicketDetailPage />} />
              <Route path="legal" element={<LegalPage />} />
              <Route path="legal/:docType" element={<LegalDetailPage />} />
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}
