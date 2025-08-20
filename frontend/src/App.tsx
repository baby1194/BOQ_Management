import React from "react";
import { Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import BOQItems from "./pages/BOQItems";
import ConcentrationSheets from "./pages/ConcentrationSheets";
import CalculationSheets from "./pages/CalculationSheets";
import FileImport from "./pages/FileImport";
import SummaryOfSubsections from "./pages/SummaryOfSubsections";

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/boq" element={<BOQItems />} />
        <Route path="/concentration" element={<ConcentrationSheets />} />
        <Route path="/calculation-sheets" element={<CalculationSheets />} />
        <Route path="/import" element={<FileImport />} />
        <Route path="/summary-subsections" element={<SummaryOfSubsections />} />
      </Routes>
    </Layout>
  );
}

export default App;
