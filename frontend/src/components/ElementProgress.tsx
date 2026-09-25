import React, { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { drawingListApi } from "../services/api";
import { formatNumber } from "../utils/format";

const ElementProgress: React.FC = () => {
  const { t } = useTranslation();
  const [elements, setElements] = useState<string[]>([]);
  const [element, setElement] = useState("");
  const [rows, setRows] = useState<
    | {
        section_number: string;
        description: string;
        contract_quantity: number;
        quantity_submitted: number;
        submitted: boolean;
      }[]
    | null
  >(null);

  useEffect(() => {
    drawingListApi.elements().then(setElements).catch(() => setElements([]));
  }, []);

  const load = async (value: string) => {
    setElement(value);
    if (!value) {
      setRows(null);
      return;
    }
    const result = await drawingListApi.elementSubmission(value);
    setRows(result.items);
  };

  return (
    <div className="bg-white rounded-lg shadow p-4 space-y-3">
      <div>
        <h2 className="text-lg font-semibold text-gray-900">
          {t("listOfDrawings.elementProgress")}
        </h2>
        <p className="text-sm text-gray-500">{t("listOfDrawings.elementProgressHint")}</p>
      </div>
      <select
        value={element}
        onChange={(event) => load(event.target.value)}
        className="border border-gray-300 rounded-md px-3 py-2 text-sm"
      >
        <option value="">{t("listOfDrawings.chooseElement")}</option>
        {elements.map((name) => (
          <option key={name} value={name}>
            {name}
          </option>
        ))}
      </select>
      {rows && rows.length === 0 && (
        <p className="text-sm text-gray-500">{t("listOfDrawings.noElementItems")}</p>
      )}
      {rows && rows.length > 0 && (
        <table className="min-w-full text-sm">
          <thead className="text-gray-600">
            <tr>
              <th className="px-2 py-1 text-start">{t("boq.sectionNumber")}</th>
              <th className="px-2 py-1 text-start">{t("boq.description")}</th>
              <th className="px-2 py-1 text-start">{t("boq.contractQty")}</th>
              <th className="px-2 py-1 text-start">{t("boq.quantitySubmitted")}</th>
              <th className="px-2 py-1 text-start">{t("listOfDrawings.submittedState")}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.section_number} className="border-t border-gray-100">
                <td className="px-2 py-1">{row.section_number}</td>
                <td className="px-2 py-1">{row.description}</td>
                <td className="px-2 py-1">{formatNumber(row.contract_quantity)}</td>
                <td className="px-2 py-1">{formatNumber(row.quantity_submitted)}</td>
                <td className={`px-2 py-1 ${row.submitted ? "text-green-700" : "text-red-700"}`}>
                  {row.submitted
                    ? t("listOfDrawings.wasSubmitted")
                    : t("listOfDrawings.notSubmitted")}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
};

export default ElementProgress;
