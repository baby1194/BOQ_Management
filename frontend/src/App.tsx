import React from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import Layout from "./components/Layout";
import ProtectedRoute from "./components/ProtectedRoute";
import Dashboard from "./pages/Dashboard";
import BOQItems from "./pages/BOQItems";
import ConcentrationSheets from "./pages/ConcentrationSheets";
import CalculationSheets from "./pages/CalculationSheets";
import FileImport from "./pages/FileImport";
import SummaryOfSubsections from "./pages/SummaryOfSubsections";
import SummaryOfSystems from "./pages/SummaryOfSystems";
import SummaryOfStructures from "./pages/SummaryOfStructures";
import SignIn from "./pages/SignIn";
import Profile from "./pages/Profile";
import { useAuth } from "./contexts/AuthContext";

function App() {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-100">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-2 text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <Routes>
      {/* Public routes */}
      <Route
        path="/signin"
        element={isAuthenticated ? <Navigate to="/" replace /> : <SignIn />}
      />

      {/* Protected routes */}
      <Route
        path="/*"
        element={
          <ProtectedRoute>
            <Layout>
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/boq" element={<BOQItems />} />
                <Route
                  path="/concentration"
                  element={<ConcentrationSheets />}
                />
                <Route
                  path="/calculation-sheets"
                  element={<CalculationSheets />}
                />
                <Route path="/import" element={<FileImport />} />
                <Route
                  path="/summary-subsections"
                  element={<SummaryOfSubsections />}
                />
                <Route path="/summary-systems" element={<SummaryOfSystems />} />
                <Route
                  path="/summary-structures"
                  element={<SummaryOfStructures />}
                />
                <Route path="/profile" element={<Profile />} />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </Layout>
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}

export default App;
