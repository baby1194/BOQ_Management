import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import toast from "react-hot-toast";
import { drawingListApi } from "../services/api";

const PlanMeasure: React.FC = () => {
  const { t } = useTranslation();
  const [filePath, setFilePath] = useState("");
  const [sectionNumber, setSectionNumber] = useState("");
  const [result, setResult] = useState<{
    length: number;
    line_count: number;
    unit_count: number;
    readable: boolean;
    detail: string;
  } | null>(null);
  const [busy, setBusy] = useState(false);

  const measure = async () => {
    setBusy(true);
    try {
      const measured = await drawingListApi.measurePlan(filePath);
      setResult(measured);
      if (!measured.readable) {
        toast.error(measured.detail);
      }
    } catch {
      toast.error(t("listOfDrawings.measureFailed"));
    } finally {
      setBusy(false);
    }
  };

  const assign = async (quantity: number) => {
    if (!sectionNumber.trim()) return;
    setBusy(true);
    try {
      const applied = await drawingListApi.assignPlanQuantity(
        sectionNumber.trim(),
        quantity
      );
      toast.success(
        t("listOfDrawings.measureAssigned", {
          section: applied.section_number,
          quantity: applied.estimated_quantity,
        })
      );
    } catch {
      toast.error(t("listOfDrawings.measureFailed"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow p-4 space-y-3">
      <div>
        <h2 className="text-lg font-semibold text-gray-900">
          {t("listOfDrawings.measurePlan")}
        </h2>
        <p className="text-sm text-gray-500">{t("listOfDrawings.measurePlanHint")}</p>
      </div>
      <div className="flex flex-wrap gap-2">
        <input
          value={filePath}
          onChange={(event) => setFilePath(event.target.value)}
          placeholder={t("listOfDrawings.planPath")}
          className="border border-gray-300 rounded-md px-3 py-2 text-sm flex-1 min-w-[16rem]"
        />
        <button
          type="button"
          onClick={measure}
          disabled={busy || !filePath.trim()}
          className="px-4 py-2 bg-slate-700 text-white rounded-md text-sm disabled:opacity-50"
        >
          {t("listOfDrawings.measure")}
        </button>
      </div>
      {result?.readable && (
        <div className="flex flex-wrap items-end gap-2 text-sm">
          <span>
            {t("listOfDrawings.planLength")}: {result.length}
          </span>
          <span>
            {t("listOfDrawings.planCount")}: {result.unit_count}
          </span>
          <input
            value={sectionNumber}
            onChange={(event) => setSectionNumber(event.target.value)}
            placeholder={t("boq.sectionNumber")}
            className="border border-gray-300 rounded-md px-3 py-2"
          />
          <button
            type="button"
            disabled={busy || !sectionNumber.trim()}
            onClick={() => assign(result.length)}
            className="px-3 py-2 bg-blue-600 text-white rounded-md disabled:opacity-50"
          >
            {t("listOfDrawings.assignLength")}
          </button>
          <button
            type="button"
            disabled={busy || !sectionNumber.trim()}
            onClick={() => assign(result.unit_count)}
            className="px-3 py-2 bg-blue-600 text-white rounded-md disabled:opacity-50"
          >
            {t("listOfDrawings.assignCount")}
          </button>
        </div>
      )}
    </div>
  );
};

export default PlanMeasure;
