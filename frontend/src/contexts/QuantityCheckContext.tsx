import React, { createContext, useCallback, useContext, useEffect, useState } from "react";
import { calculationSheetsApi } from "../services/api";
import { useProject } from "./ProjectContext";

export interface QuantityMismatch {
  section_number: string;
  sheet_calculated: number;
  system_calculated: number;
  calculated_diff: number;
  sheet_submitted: number;
  system_submitted: number;
  submitted_diff: number;
  status: string;
  has_manual_entries?: boolean;
  is_non_boq?: boolean;
}

interface QuantityCheckContextValue {
  mismatches: QuantityMismatch[] | null;
  checking: boolean;
  failed: boolean;
  runCheck: () => Promise<void>;
  close: () => void;
}

const QuantityCheckContext = createContext<QuantityCheckContextValue | undefined>(
  undefined
);

export const QuantityCheckProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const { activeProjectId } = useProject();
  const [mismatches, setMismatches] = useState<QuantityMismatch[] | null>(null);
  const [checking, setChecking] = useState(false);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    setMismatches(null);
    setFailed(false);
  }, [activeProjectId]);

  const runCheck = useCallback(async () => {
    try {
      setChecking(true);
      setFailed(false);
      const result = await calculationSheetsApi.quantityCheck();
      setMismatches(result.items);
    } catch (err) {
      console.error("Error checking quantities:", err);
      setFailed(true);
    } finally {
      setChecking(false);
    }
  }, []);

  const close = useCallback(() => {
    setMismatches(null);
    setFailed(false);
  }, []);

  return (
    <QuantityCheckContext.Provider
      value={{ mismatches, checking, failed, runCheck, close }}
    >
      {children}
    </QuantityCheckContext.Provider>
  );
};

export const useQuantityCheck = (): QuantityCheckContextValue => {
  const context = useContext(QuantityCheckContext);
  if (!context) {
    throw new Error("useQuantityCheck must be used inside QuantityCheckProvider");
  }
  return context;
};
