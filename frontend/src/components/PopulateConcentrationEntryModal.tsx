import React, { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { useLanguage } from "../contexts/LanguageContext";
import { BOQItem } from "../types";

interface PopulateConcentrationEntryModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (boqItemIds: number[]) => void;
  boqItems: BOQItem[];
  currentBoqItemId: number;
  listLoading: boolean;
  submitLoading: boolean;
}

const PopulateConcentrationEntryModal: React.FC<
  PopulateConcentrationEntryModalProps
> = ({
  isOpen,
  onClose,
  onConfirm,
  boqItems,
  currentBoqItemId,
  listLoading,
  submitLoading,
}) => {
  const { t } = useTranslation();
  const { isRTL } = useLanguage();
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [filter, setFilter] = useState("");

  useEffect(() => {
    if (isOpen) {
      setSelected(new Set());
      setFilter("");
    }
  }, [isOpen]);

  const sortedItems = useMemo(() => {
    return [...boqItems].sort((a, b) =>
      a.section_number.localeCompare(b.section_number, undefined, {
        numeric: true,
      }),
    );
  }, [boqItems]);

  const filteredItems = useMemo(() => {
    const q = filter.trim().toLowerCase();
    if (!q) return sortedItems;
    return sortedItems.filter(
      (item) =>
        item.section_number.toLowerCase().includes(q) ||
        (item.description || "").toLowerCase().includes(q),
    );
  }, [sortedItems, filter]);

  const toggle = (id: number) => {
    if (id === currentBoqItemId) return;
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const selectAllVisible = () => {
    setSelected((prev) => {
      const next = new Set(prev);
      for (const item of filteredItems) {
        if (item.id !== currentBoqItemId) next.add(item.id);
      }
      return next;
    });
  };

  const deselectAll = () => setSelected(new Set());

  const handleConfirm = () => {
    const ids = Array.from(selected).filter((id) => id !== currentBoqItemId);
    if (ids.length === 0) return;
    onConfirm(ids);
  };

  if (!isOpen) return null;

  const busy = submitLoading || listLoading;
  const selectedCount = Array.from(selected).filter(
    (id) => id !== currentBoqItemId,
  ).length;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div
        className="bg-white rounded-lg p-6 w-full max-w-lg mx-4 max-h-[90vh] flex flex-col shadow-lg"
        dir={isRTL ? "rtl" : "ltr"}
      >
        <div
          className={`flex justify-between items-center mb-4 shrink-0 ${
            isRTL ? "flex-row-reverse" : ""
          }`}
        >
          <h2 className="text-xl font-semibold text-gray-900">
            {t("concentration.populateEntryTitle")}
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
            disabled={busy}
          >
            <svg
              className="w-6 h-6"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        <p className="text-sm text-gray-600 mb-3 shrink-0">
          {t("concentration.populateEntryDescription")}
        </p>

        <input
          type="search"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          placeholder={t("common.search")}
          disabled={busy}
          className="w-full px-3 py-2 border border-gray-300 rounded-md mb-3 shrink-0 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />

        <div className={`flex gap-2 mb-3 shrink-0 ${isRTL ? "flex-row-reverse" : ""}`}>
          <button
            type="button"
            onClick={selectAllVisible}
            className="px-3 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
            disabled={busy || filteredItems.length === 0}
          >
            {t("common.selectAll")}
          </button>
          <button
            type="button"
            onClick={deselectAll}
            className="px-3 py-1 text-xs border border-gray-300 rounded text-gray-700 hover:bg-gray-50 disabled:opacity-50"
            disabled={busy || filteredItems.length === 0}
          >
            {t("common.deselectAll")}
          </button>
        </div>

        <div className="flex-1 min-h-0 border border-gray-200 rounded-md overflow-y-auto">
          {listLoading ? (
            <div className="flex justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
            </div>
          ) : filteredItems.length === 0 ? (
            <p className="text-sm text-gray-500 p-4 text-center">
              {t("common.noValuesFound")}
            </p>
          ) : (
            <ul className="divide-y divide-gray-100">
              {filteredItems.map((item) => {
                const isCurrent = item.id === currentBoqItemId;
                const checked = selected.has(item.id);
                return (
                  <li key={item.id}>
                    <label
                      className={`flex items-center gap-3 px-3 py-2 cursor-pointer hover:bg-gray-50 ${
                        isCurrent ? "opacity-60 cursor-not-allowed" : ""
                      } ${isRTL ? "flex-row-reverse" : ""}`}
                    >
                      <input
                        type="checkbox"
                        checked={checked && !isCurrent}
                        disabled={busy || isCurrent}
                        onChange={() => toggle(item.id)}
                        className="rounded border-gray-300 text-blue-600 focus:ring-blue-500 shrink-0"
                      />
                      <div className="flex-1 min-w-0 text-sm">
                        <div className="font-medium text-gray-900 truncate">
                          {item.section_number}
                          {isCurrent ? (
                            <span className="text-gray-500 font-normal ms-2">
                              ({t("concentration.currentSheetItem")})
                            </span>
                          ) : null}
                        </div>
                        <div className="text-gray-600 truncate">
                          {item.description || "—"}
                        </div>
                      </div>
                    </label>
                  </li>
                );
              })}
            </ul>
          )}
        </div>

        <div
          className={`flex justify-between items-center mt-4 pt-4 border-t border-gray-200 shrink-0 ${
            isRTL ? "flex-row-reverse" : ""
          }`}
        >
          <span className="text-sm text-gray-600">
            {t("concentration.populateSelectedCount", { count: selectedCount })}
          </span>
          <div className={`flex gap-2 ${isRTL ? "flex-row-reverse" : ""}`}>
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50 disabled:opacity-50"
              disabled={busy}
            >
              {t("common.cancel")}
            </button>
            <button
              type="button"
              onClick={handleConfirm}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
              disabled={busy || selectedCount === 0}
            >
              {submitLoading
                ? t("common.loading")
                : t("concentration.populateConfirm")}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PopulateConcentrationEntryModal;
