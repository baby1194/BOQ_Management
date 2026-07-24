import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import toast from "react-hot-toast";
import { DraftingCompass, Plus, Pencil, Trash2, Copy } from "lucide-react";
import { useLanguage } from "../contexts/LanguageContext";
import FilterDropdown from "../components/FilterDropdown";
import { drawingListApi } from "../services/api";
import { DrawingListItem } from "../types";
import {
  filterCellValue,
  matchesSelectedFilter,
  sortUniqueValues,
  useColumnDropdownFilters,
} from "../utils/columnFilters";

interface DraftFields {
  no: string;
  drawing_type: string;
  planning_office: string;
  drawing_name: string;
  cross_sections: string;
  element: string;
  sheet_name: string;
  edition: string;
  release_date: string;
  update_description: string;
  folder_date: string;
  file_path: string;
  notes: string;
  execution_status: "" | "to_be_executed" | "cancelled";
}

type EditingState =
  | { mode: "new"; draft: DraftFields }
  | { mode: "edit"; id: number; draft: DraftFields }
  | null;

const emptyDraft = (suggestedNo?: number): DraftFields => ({
  no: suggestedNo != null ? String(suggestedNo) : "",
  drawing_type: "",
  planning_office: "",
  drawing_name: "",
  cross_sections: "",
  element: "",
  sheet_name: "",
  edition: "",
  release_date: "",
  update_description: "",
  folder_date: "",
  file_path: "",
  notes: "",
  execution_status: "",
});

const rowToDraft = (row: DrawingListItem): DraftFields => ({
  no: String(row.no),
  drawing_type: row.drawing_type || "",
  planning_office: row.planning_office || "",
  drawing_name: row.drawing_name || "",
  cross_sections: row.cross_sections || "",
  element: row.element || "",
  sheet_name: row.sheet_name || "",
  edition: row.edition || "",
  release_date: row.release_date || "",
  update_description: row.update_description || "",
  folder_date: row.folder_date || "",
  file_path: row.file_path || "",
  notes: row.notes || "",
  execution_status:
    row.execution_status === "to_be_executed" ||
    row.execution_status === "cancelled"
      ? row.execution_status
      : "",
});

const cellClass =
  "px-2 py-2 text-sm text-gray-900 text-center border border-gray-300 align-middle";
const inputClass =
  "w-full min-w-[5.5rem] px-1.5 py-1 text-sm border border-blue-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 text-center";

const COLUMN_KEYS = [
  "no",
  "drawingType",
  "planningOffice",
  "drawingName",
  "crossSections",
  "element",
  "sheetName",
  "edition",
  "releaseDate",
  "updateDescription",
  "folderDate",
  "filePath",
  "notes",
  "executionStatus",
  "action",
] as const;

const FILTER_KEYS = [
  "no",
  "drawingType",
  "planningOffice",
  "drawingName",
  "crossSections",
  "element",
  "sheetName",
  "edition",
  "releaseDate",
  "updateDescription",
  "folderDate",
  "filePath",
  "notes",
  "executionStatus",
] as const;

type FilterKey = (typeof FILTER_KEYS)[number];

const ListOfDrawings: React.FC = () => {
  const { t } = useTranslation();
  const { isRTL } = useLanguage();
  const [items, setItems] = useState<DrawingListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [editing, setEditing] = useState<EditingState>(null);
  const [openingId, setOpeningId] = useState<number | null>(null);

  const {
    selected,
    open,
    activeFilterCount,
    handleSelectionChange,
    handleClear,
    handleClearAll,
    handleToggle,
    handleClose,
  } = useColumnDropdownFilters(FILTER_KEYS);

  const statusFilterValue = useCallback(
    (status?: string | null) => {
      if (status === "to_be_executed") return t("listOfDrawings.toBeExecuted");
      if (status === "cancelled") return t("listOfDrawings.cancelled");
      return "";
    },
    [t]
  );

  const getRowFilterValues = useCallback(
    (row: DrawingListItem): Record<FilterKey, string> => ({
      no: filterCellValue(row.no),
      drawingType: filterCellValue(row.drawing_type),
      planningOffice: filterCellValue(row.planning_office),
      drawingName: filterCellValue(row.drawing_name),
      crossSections: filterCellValue(row.cross_sections),
      element: filterCellValue(row.element),
      sheetName: filterCellValue(row.sheet_name),
      edition: filterCellValue(row.edition),
      releaseDate: filterCellValue(row.release_date),
      updateDescription: filterCellValue(row.update_description),
      folderDate: filterCellValue(row.folder_date),
      filePath: filterCellValue(row.file_path),
      notes: filterCellValue(row.notes),
      executionStatus: statusFilterValue(row.execution_status),
    }),
    [statusFilterValue]
  );

  const loadItems = useCallback(async () => {
    try {
      setLoading(true);
      const data = await drawingListApi.getAll();
      setItems(data);
    } catch (error: any) {
      console.error(error);
      toast.error(
        error?.response?.data?.detail || t("listOfDrawings.failedToLoad")
      );
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    loadItems();
  }, [loadItems]);

  const uniqueValues = useMemo(() => {
    const buckets = Object.fromEntries(
      FILTER_KEYS.map((key) => [key, [] as string[]])
    ) as Record<FilterKey, string[]>;
    items.forEach((row) => {
      const values = getRowFilterValues(row);
      FILTER_KEYS.forEach((key) => buckets[key].push(values[key]));
    });
    return Object.fromEntries(
      FILTER_KEYS.map((key) => [key, sortUniqueValues(buckets[key])])
    ) as Record<FilterKey, string[]>;
  }, [items, getRowFilterValues]);

  const filteredItems = useMemo(() => {
    return items.filter((row) => {
      const values = getRowFilterValues(row);
      return FILTER_KEYS.every((key) =>
        matchesSelectedFilter(values[key], selected[key])
      );
    });
  }, [items, selected, getRowFilterValues]);

  const updateDraft = (patch: Partial<DraftFields>) => {
    setEditing((prev) => (prev ? { ...prev, draft: { ...prev.draft, ...patch } } : prev));
  };

  const handleAddRow = () => {
    setEditing({
      mode: "new",
      draft: emptyDraft(items.length + 1),
    });
  };

  const startEdit = (row: DrawingListItem) => {
    setEditing({ mode: "edit", id: row.id, draft: rowToDraft(row) });
  };

  const handleDuplicate = (row: DrawingListItem) => {
    const draft = rowToDraft(row);
    draft.no = "";
    setEditing({ mode: "new", draft });
  };

  const cancelEdit = () => setEditing(null);

  const parseNo = (raw: string): number | null | undefined => {
    const trimmed = raw.trim();
    if (trimmed === "") return null;
    const parsed = Number(trimmed);
    if (!Number.isInteger(parsed) || parsed < 1) {
      toast.error(t("listOfDrawings.invalidNo"));
      return undefined;
    }
    return parsed;
  };

  const draftToPayload = (draft: DraftFields) => {
    const no = parseNo(draft.no);
    if (no === undefined) return null;
    return {
      no,
      drawing_type: draft.drawing_type.trim() || null,
      planning_office: draft.planning_office.trim() || null,
      drawing_name: draft.drawing_name.trim() || null,
      cross_sections: draft.cross_sections.trim() || null,
      element: draft.element.trim() || null,
      sheet_name: draft.sheet_name.trim() || null,
      edition: draft.edition.trim() || null,
      release_date: draft.release_date.trim() || null,
      update_description: draft.update_description.trim() || null,
      folder_date: draft.folder_date.trim() || null,
      file_path: draft.file_path.trim() || null,
      notes: draft.notes.trim() || null,
      execution_status: draft.execution_status || null,
    };
  };

  const saveEditing = async () => {
    if (!editing) return;
    const payload = draftToPayload(editing.draft);
    if (!payload) return;

    setSaving(true);
    try {
      if (editing.mode === "new") {
        await drawingListApi.create(payload);
        toast.success(t("listOfDrawings.createdSuccessfully"));
      } else {
        await drawingListApi.update(editing.id, payload);
        toast.success(t("listOfDrawings.updatedSuccessfully"));
      }
      setEditing(null);
      await loadItems();
    } catch (error: any) {
      console.error(error);
      toast.error(
        error?.response?.data?.detail ||
          (editing.mode === "new"
            ? t("listOfDrawings.failedToCreate")
            : t("listOfDrawings.failedToUpdate"))
      );
    } finally {
      setSaving(false);
    }
  };

  const handleEditKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void saveEditing();
    } else if (e.key === "Escape") {
      cancelEdit();
    }
  };

  const handleDelete = async (row: DrawingListItem) => {
    const label =
      row.drawing_name || row.sheet_name || row.file_path || `#${row.no}`;
    const confirmed = window.confirm(
      t("listOfDrawings.confirmDelete", { name: label })
    );
    if (!confirmed) return;

    try {
      await drawingListApi.delete(row.id);
      if (editing?.mode === "edit" && editing.id === row.id) cancelEdit();
      toast.success(t("listOfDrawings.deletedSuccessfully"));
      await loadItems();
    } catch (error: any) {
      console.error(error);
      toast.error(
        error?.response?.data?.detail || t("listOfDrawings.failedToDelete")
      );
    }
  };

  const handleOpenFile = async (row: DrawingListItem) => {
    if (!row.file_path) {
      toast.error(t("listOfDrawings.noFilePath"));
      return;
    }
    setOpeningId(row.id);
    try {
      await drawingListApi.open(row.id);
    } catch (error: any) {
      console.error(error);
      toast.error(
        error?.response?.data?.detail || t("listOfDrawings.failedToOpen")
      );
    } finally {
      setOpeningId(null);
    }
  };

  const statusLabel = (status?: string | null) => {
    if (status === "to_be_executed") return t("listOfDrawings.toBeExecuted");
    if (status === "cancelled") return t("listOfDrawings.cancelled");
    return "—";
  };

  const thClass =
    "px-2 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider whitespace-nowrap text-center border border-gray-300 bg-gray-50";

  const renderDraftInputs = (draft: DraftFields) => (
    <>
      <td className={cellClass}>
        <input
          type="number"
          min={1}
          value={draft.no}
          onChange={(e) => updateDraft({ no: e.target.value })}
          onKeyDown={handleEditKeyDown}
          className={inputClass}
          autoFocus
        />
      </td>
      <td className={cellClass}>
        <input
          type="text"
          value={draft.drawing_type}
          onChange={(e) => updateDraft({ drawing_type: e.target.value })}
          onKeyDown={handleEditKeyDown}
          className={inputClass}
        />
      </td>
      <td className={cellClass}>
        <input
          type="text"
          value={draft.planning_office}
          onChange={(e) => updateDraft({ planning_office: e.target.value })}
          onKeyDown={handleEditKeyDown}
          className={inputClass}
        />
      </td>
      <td className={cellClass}>
        <input
          type="text"
          value={draft.drawing_name}
          onChange={(e) => updateDraft({ drawing_name: e.target.value })}
          onKeyDown={handleEditKeyDown}
          className={inputClass}
        />
      </td>
      <td className={cellClass}>
        <input
          type="text"
          value={draft.cross_sections}
          onChange={(e) => updateDraft({ cross_sections: e.target.value })}
          onKeyDown={handleEditKeyDown}
          className={inputClass}
        />
      </td>
      <td className={cellClass}>
        <input
          type="text"
          value={draft.element}
          onChange={(e) => updateDraft({ element: e.target.value })}
          onKeyDown={handleEditKeyDown}
          className={inputClass}
        />
      </td>
      <td className={cellClass}>
        <input
          type="text"
          value={draft.sheet_name}
          onChange={(e) => updateDraft({ sheet_name: e.target.value })}
          onKeyDown={handleEditKeyDown}
          className={inputClass}
        />
      </td>
      <td className={cellClass}>
        <input
          type="text"
          value={draft.edition}
          onChange={(e) => updateDraft({ edition: e.target.value })}
          onKeyDown={handleEditKeyDown}
          className={inputClass}
        />
      </td>
      <td className={cellClass}>
        <input
          type="text"
          value={draft.release_date}
          onChange={(e) => updateDraft({ release_date: e.target.value })}
          onKeyDown={handleEditKeyDown}
          className={inputClass}
          placeholder={t("listOfDrawings.datePlaceholder")}
        />
      </td>
      <td className={cellClass}>
        <input
          type="text"
          value={draft.update_description}
          onChange={(e) => updateDraft({ update_description: e.target.value })}
          onKeyDown={handleEditKeyDown}
          className={`${inputClass} min-w-[8rem]`}
        />
      </td>
      <td className={cellClass}>
        <input
          type="text"
          value={draft.folder_date}
          onChange={(e) => updateDraft({ folder_date: e.target.value })}
          onKeyDown={handleEditKeyDown}
          className={inputClass}
          placeholder={t("listOfDrawings.datePlaceholder")}
        />
      </td>
      <td className={cellClass}>
        <input
          type="text"
          value={draft.file_path}
          onChange={(e) => updateDraft({ file_path: e.target.value })}
          onKeyDown={handleEditKeyDown}
          className={`${inputClass} min-w-[12rem]`}
          placeholder={t("listOfDrawings.filePathPlaceholder")}
        />
      </td>
      <td className={cellClass}>
        <input
          type="text"
          value={draft.notes}
          onChange={(e) => updateDraft({ notes: e.target.value })}
          onKeyDown={handleEditKeyDown}
          className={`${inputClass} min-w-[7rem]`}
        />
      </td>
      <td className={cellClass}>
        <select
          value={draft.execution_status}
          onChange={(e) =>
            updateDraft({
              execution_status: e.target.value as DraftFields["execution_status"],
            })
          }
          onKeyDown={handleEditKeyDown}
          className={inputClass}
        >
          <option value="">—</option>
          <option value="to_be_executed">
            {t("listOfDrawings.toBeExecuted")}
          </option>
          <option value="cancelled">{t("listOfDrawings.cancelled")}</option>
        </select>
      </td>
      <td className={cellClass}>
        <div
          className={`inline-flex items-center justify-center gap-2 ${
            isRTL ? "flex-row-reverse" : ""
          }`}
        >
          <button
            type="button"
            onClick={() => void saveEditing()}
            disabled={saving}
            className="inline-flex items-center px-2.5 py-1.5 text-xs font-medium text-white bg-blue-600 rounded hover:bg-blue-700 disabled:opacity-50"
          >
            {editing?.mode === "new"
              ? t("listOfDrawings.add")
              : t("common.save")}
          </button>
          <button
            type="button"
            onClick={cancelEdit}
            className="inline-flex items-center px-2.5 py-1.5 text-xs font-medium text-gray-700 bg-gray-100 rounded hover:bg-gray-200"
          >
            {t("common.cancel")}
          </button>
        </div>
      </td>
    </>
  );

  const renderReadRow = (row: DrawingListItem) => (
    <>
      <td className={cellClass}>{row.no}</td>
      <td className={cellClass}>{row.drawing_type || "—"}</td>
      <td className={cellClass}>{row.planning_office || "—"}</td>
      <td className={cellClass}>{row.drawing_name || "—"}</td>
      <td className={cellClass}>{row.cross_sections || "—"}</td>
      <td className={cellClass}>{row.element || "—"}</td>
      <td className={cellClass}>{row.sheet_name || "—"}</td>
      <td className={cellClass}>{row.edition || "—"}</td>
      <td className={cellClass}>{row.release_date || "—"}</td>
      <td className={cellClass}>
        <span className="whitespace-pre-wrap">
          {row.update_description || "—"}
        </span>
      </td>
      <td className={cellClass}>{row.folder_date || "—"}</td>
      <td className={`${cellClass} max-w-xs`}>
        {row.file_path ? (
          <button
            type="button"
            onClick={() => handleOpenFile(row)}
            disabled={openingId === row.id}
            className="text-blue-600 hover:text-blue-800 hover:underline break-all text-center"
            title={t("listOfDrawings.openFile")}
          >
            {row.file_path}
          </button>
        ) : (
          "—"
        )}
      </td>
      <td className={cellClass}>
        <span className="whitespace-pre-wrap">{row.notes || "—"}</span>
      </td>
      <td className={cellClass}>{statusLabel(row.execution_status)}</td>
      <td className={cellClass}>
        <div
          className={`inline-flex items-center justify-center gap-2 ${
            isRTL ? "flex-row-reverse" : ""
          }`}
        >
          <button
            type="button"
            onClick={() => startEdit(row)}
            disabled={editing?.mode === "new"}
            className={`inline-flex items-center px-2.5 py-1.5 text-xs font-medium text-blue-700 bg-blue-50 rounded hover:bg-blue-100 disabled:opacity-50 ${
              isRTL ? "flex-row-reverse" : ""
            }`}
          >
            <Pencil className={`h-3.5 w-3.5 ${isRTL ? "ml-1" : "mr-1"}`} />
            {t("common.edit")}
          </button>
          <button
            type="button"
            onClick={() => handleDuplicate(row)}
            disabled={editing?.mode === "new"}
            className={`inline-flex items-center px-2.5 py-1.5 text-xs font-medium text-indigo-700 bg-indigo-50 rounded hover:bg-indigo-100 disabled:opacity-50 ${
              isRTL ? "flex-row-reverse" : ""
            }`}
          >
            <Copy className={`h-3.5 w-3.5 ${isRTL ? "ml-1" : "mr-1"}`} />
            {t("listOfDrawings.duplicate")}
          </button>
          <button
            type="button"
            onClick={() => handleDelete(row)}
            className={`inline-flex items-center px-2.5 py-1.5 text-xs font-medium text-red-700 bg-red-50 rounded hover:bg-red-100 ${
              isRTL ? "flex-row-reverse" : ""
            }`}
          >
            <Trash2 className={`h-3.5 w-3.5 ${isRTL ? "ml-1" : "mr-1"}`} />
            {t("common.delete")}
          </button>
        </div>
      </td>
    </>
  );

  return (
    <div className="space-y-6" dir={isRTL ? "rtl" : "ltr"}>
      <div
        className={`flex flex-wrap items-center justify-between gap-4 ${
          isRTL ? "flex-row-reverse" : ""
        }`}
      >
        <div className={isRTL ? "text-right" : "text-left"}>
          <h1 className="text-2xl font-bold text-gray-900">
            {t("listOfDrawings.title")}
          </h1>
          <p className="mt-1 text-sm text-gray-500">
            {t("listOfDrawings.subtitle")}
          </p>
        </div>
        <div
          className={`flex flex-wrap items-center gap-2 ${
            isRTL ? "flex-row-reverse" : ""
          }`}
        >
          {activeFilterCount > 0 && (
            <button
              type="button"
              onClick={handleClearAll}
              className="px-3 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200"
            >
              {t("common.clearFilter")} ({activeFilterCount})
            </button>
          )}
          <button
            type="button"
            onClick={handleAddRow}
            disabled={editing?.mode === "new"}
            className={`inline-flex items-center px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 transition-colors disabled:opacity-50 ${
              isRTL ? "flex-row-reverse" : ""
            }`}
          >
            <Plus className={`h-4 w-4 ${isRTL ? "ml-2" : "mr-2"}`} />
            {t("listOfDrawings.addDrawing")}
          </button>
        </div>
      </div>

      <div className="bg-white border border-gray-200 rounded-lg shadow-sm overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center py-16 text-gray-500">
            {t("common.loading")}
          </div>
        ) : items.length === 0 && editing?.mode !== "new" ? (
          <div className="flex flex-col items-center justify-center py-16 text-gray-500">
            <DraftingCompass className="h-10 w-10 mb-3 text-gray-300" />
            <p>{t("listOfDrawings.empty")}</p>
          </div>
        ) : (
          <>
            {activeFilterCount > 0 && (
              <div className="px-4 py-2 text-sm text-gray-600 border-b border-gray-200 bg-gray-50">
                {filteredItems.length} / {items.length} {t("common.items")}
              </div>
            )}
            <div className="overflow-auto max-h-[70vh]">
              <table className="min-w-full border-collapse">
                <thead className="sticky top-0 z-10 bg-gray-50 shadow-sm">
                  <tr>
                    {COLUMN_KEYS.map((key) =>
                      key === "action" ? (
                        <th key={key} className={thClass}>
                          {t(`listOfDrawings.${key}`)}
                        </th>
                      ) : (
                        <th key={key} className={thClass}>
                          <div className="flex items-center justify-center gap-1">
                            <span>{t(`listOfDrawings.${key}`)}</span>
                            <FilterDropdown
                              columnName={t(`listOfDrawings.${key}`)}
                              values={uniqueValues[key as FilterKey]}
                              selectedValues={selected[key as FilterKey]}
                              onSelectionChange={(values) =>
                                handleSelectionChange(key as FilterKey, values)
                              }
                              onClearFilter={() =>
                                handleClear(key as FilterKey)
                              }
                              isOpen={open[key as FilterKey]}
                              onToggle={() => handleToggle(key as FilterKey)}
                              onClose={() => handleClose(key as FilterKey)}
                            />
                          </div>
                        </th>
                      )
                    )}
                  </tr>
                </thead>
                <tbody className="bg-white">
                  {filteredItems.length === 0 && editing?.mode !== "new" ? (
                    <tr>
                      <td
                        colSpan={COLUMN_KEYS.length}
                        className="px-4 py-8 text-center text-sm text-gray-500 border border-gray-300"
                      >
                        {t("common.noValuesFound")}
                      </td>
                    </tr>
                  ) : (
                    filteredItems.map((row) => {
                      const isEditing =
                        editing?.mode === "edit" && editing.id === row.id;
                      return (
                        <tr key={row.id} className="hover:bg-gray-50">
                          {isEditing && editing
                            ? renderDraftInputs(editing.draft)
                            : renderReadRow(row)}
                        </tr>
                      );
                    })
                  )}
                  {editing?.mode === "new" && (
                    <tr className="bg-blue-50/40">
                      {renderDraftInputs(editing.draft)}
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default ListOfDrawings;
