import React, { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import toast from "react-hot-toast";
import { FolderOpen, Plus, Pencil, Trash2, X } from "lucide-react";
import { useLanguage } from "../contexts/LanguageContext";
import { projectInfoFilesApi } from "../services/api";
import { ProjectInfoFile } from "../types";

interface AddFormState {
  no: string;
  category_en: string;
  category_he: string;
  file_path: string;
  description: string;
}

interface EditDraft {
  file_path: string;
  description: string;
}

const emptyAddForm = (): AddFormState => ({
  no: "",
  category_en: "",
  category_he: "",
  file_path: "",
  description: "",
});

const ProjectInfoFiles: React.FC = () => {
  const { t } = useTranslation();
  const { isRTL, language } = useLanguage();
  const [files, setFiles] = useState<ProjectInfoFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  const [addForm, setAddForm] = useState<AddFormState>(emptyAddForm);
  const [saving, setSaving] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editDraft, setEditDraft] = useState<EditDraft>({
    file_path: "",
    description: "",
  });
  const [openingId, setOpeningId] = useState<number | null>(null);

  const loadFiles = useCallback(async () => {
    try {
      setLoading(true);
      const data = await projectInfoFilesApi.getAll();
      setFiles(data);
    } catch (error: any) {
      console.error(error);
      toast.error(
        error?.response?.data?.detail || t("projectInfoFiles.failedToLoad")
      );
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    loadFiles();
  }, [loadFiles]);

  const categoryForRow = (row: ProjectInfoFile) =>
    language === "he" ? row.category_he : row.category_en;

  const handleOpenAdd = () => {
    setAddForm(emptyAddForm());
    setShowAddForm(true);
    setEditingId(null);
  };

  const handleCreate = async (e?: React.FormEvent) => {
    e?.preventDefault();
    const categoryEn = addForm.category_en.trim();
    const categoryHe = addForm.category_he.trim();
    const filePath = addForm.file_path.trim();

    if (!categoryEn || !categoryHe || !filePath) {
      toast.error(t("projectInfoFiles.requiredFields"));
      return;
    }

    const noRaw = addForm.no.trim();
    let no: number | null = null;
    if (noRaw !== "") {
      const parsed = Number(noRaw);
      if (!Number.isInteger(parsed) || parsed < 1) {
        toast.error(t("projectInfoFiles.invalidNo"));
        return;
      }
      no = parsed;
    }

    setSaving(true);
    try {
      await projectInfoFilesApi.create({
        no,
        category_en: categoryEn,
        category_he: categoryHe,
        file_path: filePath,
        description: addForm.description.trim() || null,
      });
      toast.success(t("projectInfoFiles.createdSuccessfully"));
      setShowAddForm(false);
      setAddForm(emptyAddForm());
      await loadFiles();
    } catch (error: any) {
      console.error(error);
      toast.error(
        error?.response?.data?.detail || t("projectInfoFiles.failedToCreate")
      );
    } finally {
      setSaving(false);
    }
  };

  const startEdit = (row: ProjectInfoFile) => {
    setShowAddForm(false);
    setEditingId(row.id);
    setEditDraft({
      file_path: row.file_path,
      description: row.description || "",
    });
  };

  const cancelEdit = () => {
    setEditingId(null);
    setEditDraft({ file_path: "", description: "" });
  };

  const saveEdit = async (id: number) => {
    const filePath = editDraft.file_path.trim();
    if (!filePath) {
      toast.error(t("projectInfoFiles.filePathRequired"));
      return;
    }

    setSaving(true);
    try {
      const updated = await projectInfoFilesApi.update(id, {
        file_path: filePath,
        description: editDraft.description.trim() || null,
      });
      setFiles((prev) => prev.map((f) => (f.id === id ? updated : f)));
      setEditingId(null);
      toast.success(t("projectInfoFiles.updatedSuccessfully"));
    } catch (error: any) {
      console.error(error);
      toast.error(
        error?.response?.data?.detail || t("projectInfoFiles.failedToUpdate")
      );
    } finally {
      setSaving(false);
    }
  };

  const handleEditKeyDown = (
    e: React.KeyboardEvent,
    id: number
  ) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void saveEdit(id);
    } else if (e.key === "Escape") {
      cancelEdit();
    }
  };

  const handleDelete = async (row: ProjectInfoFile) => {
    const confirmed = window.confirm(
      t("projectInfoFiles.confirmDelete", {
        name: row.file_name || row.file_path,
      })
    );
    if (!confirmed) return;

    try {
      await projectInfoFilesApi.delete(row.id);
      if (editingId === row.id) cancelEdit();
      toast.success(t("projectInfoFiles.deletedSuccessfully"));
      await loadFiles();
    } catch (error: any) {
      console.error(error);
      toast.error(
        error?.response?.data?.detail || t("projectInfoFiles.failedToDelete")
      );
    }
  };

  const handleOpenFile = async (row: ProjectInfoFile) => {
    setOpeningId(row.id);
    try {
      await projectInfoFilesApi.open(row.id);
    } catch (error: any) {
      console.error(error);
      toast.error(
        error?.response?.data?.detail || t("projectInfoFiles.failedToOpen")
      );
    } finally {
      setOpeningId(null);
    }
  };

  return (
    <div className="space-y-6" dir={isRTL ? "rtl" : "ltr"}>
      <div
        className={`flex flex-wrap items-center justify-between gap-4 ${
          isRTL ? "flex-row-reverse" : ""
        }`}
      >
        <div className={isRTL ? "text-right" : "text-left"}>
          <h1 className="text-2xl font-bold text-gray-900">
            {t("projectInfoFiles.title")}
          </h1>
          <p className="mt-1 text-sm text-gray-500">
            {t("projectInfoFiles.subtitle")}
          </p>
        </div>
        <button
          type="button"
          onClick={handleOpenAdd}
          className={`inline-flex items-center px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 transition-colors ${
            isRTL ? "flex-row-reverse" : ""
          }`}
        >
          <Plus className={`h-4 w-4 ${isRTL ? "ml-2" : "mr-2"}`} />
          {t("projectInfoFiles.addNewFile")}
        </button>
      </div>

      {showAddForm && (
        <form
          onSubmit={handleCreate}
          className="bg-white border border-gray-200 rounded-lg shadow-sm p-5 space-y-4"
        >
          <div
            className={`flex items-center justify-between ${
              isRTL ? "flex-row-reverse" : ""
            }`}
          >
            <h2 className="text-lg font-semibold text-gray-900">
              {t("projectInfoFiles.addNewFile")}
            </h2>
            <button
              type="button"
              onClick={() => setShowAddForm(false)}
              className="p-1 text-gray-400 hover:text-gray-600"
              aria-label={t("common.close")}
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t("projectInfoFiles.no")}
              </label>
              <input
                type="number"
                min={1}
                value={addForm.no}
                onChange={(e) =>
                  setAddForm((prev) => ({ ...prev, no: e.target.value }))
                }
                placeholder={t("projectInfoFiles.noPlaceholder")}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <p className="mt-1 text-xs text-gray-500">
                {t("projectInfoFiles.noHint")}
              </p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t("projectInfoFiles.filePath")}{" "}
                <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={addForm.file_path}
                onChange={(e) =>
                  setAddForm((prev) => ({
                    ...prev,
                    file_path: e.target.value,
                  }))
                }
                required
                placeholder={t("projectInfoFiles.filePathPlaceholder")}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t("projectInfoFiles.categoryEn")}{" "}
                <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={addForm.category_en}
                onChange={(e) =>
                  setAddForm((prev) => ({
                    ...prev,
                    category_en: e.target.value,
                  }))
                }
                required
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t("projectInfoFiles.categoryHe")}{" "}
                <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={addForm.category_he}
                onChange={(e) =>
                  setAddForm((prev) => ({
                    ...prev,
                    category_he: e.target.value,
                  }))
                }
                required
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                dir="rtl"
              />
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t("projectInfoFiles.description")}
              </label>
              <textarea
                value={addForm.description}
                onChange={(e) =>
                  setAddForm((prev) => ({
                    ...prev,
                    description: e.target.value,
                  }))
                }
                rows={2}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          <div
            className={`flex gap-2 ${isRTL ? "flex-row-reverse" : ""}`}
          >
            <button
              type="submit"
              disabled={saving}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50"
            >
              {saving ? t("common.loading") : t("common.create")}
            </button>
            <button
              type="button"
              onClick={() => setShowAddForm(false)}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200"
            >
              {t("common.cancel")}
            </button>
          </div>
        </form>
      )}

      <div className="bg-white border border-gray-200 rounded-lg shadow-sm overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center py-16 text-gray-500">
            {t("common.loading")}
          </div>
        ) : files.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-gray-500">
            <FolderOpen className="h-10 w-10 mb-3 text-gray-300" />
            <p>{t("projectInfoFiles.empty")}</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full border-collapse">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider whitespace-nowrap text-center border border-gray-300">
                    {t("projectInfoFiles.no")}
                  </th>
                  <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider whitespace-nowrap text-center border border-gray-300">
                    {t("projectInfoFiles.category")}
                  </th>
                  <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider whitespace-nowrap text-center border border-gray-300">
                    {t("projectInfoFiles.fileName")}
                  </th>
                  <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider whitespace-nowrap text-center border border-gray-300">
                    {t("projectInfoFiles.filePath")}
                  </th>
                  <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider text-center border border-gray-300">
                    {t("projectInfoFiles.description")}
                  </th>
                  <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider whitespace-nowrap text-center border border-gray-300">
                    {t("projectInfoFiles.action")}
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white">
                {files.map((row) => {
                  const isEditing = editingId === row.id;
                  return (
                    <tr key={row.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 text-sm text-gray-900 whitespace-nowrap text-center border border-gray-300 align-middle">
                        {row.no}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-900 whitespace-nowrap text-center border border-gray-300 align-middle">
                        {categoryForRow(row)}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-900 whitespace-nowrap text-center border border-gray-300 align-middle">
                        {row.file_name}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-900 max-w-xs text-center border border-gray-300 align-middle">
                        {isEditing ? (
                          <input
                            type="text"
                            value={editDraft.file_path}
                            onChange={(e) =>
                              setEditDraft((prev) => ({
                                ...prev,
                                file_path: e.target.value,
                              }))
                            }
                            onKeyDown={(e) => handleEditKeyDown(e, row.id)}
                            className="w-full min-w-[14rem] px-2 py-1 border border-blue-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 text-center"
                            autoFocus
                          />
                        ) : (
                          <button
                            type="button"
                            onClick={() => handleOpenFile(row)}
                            disabled={openingId === row.id}
                            className="text-blue-600 hover:text-blue-800 hover:underline break-all text-center"
                            title={t("projectInfoFiles.openFile")}
                          >
                            {row.file_path}
                          </button>
                        )}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-700 max-w-md text-center border border-gray-300 align-middle">
                        {isEditing ? (
                          <input
                            type="text"
                            value={editDraft.description}
                            onChange={(e) =>
                              setEditDraft((prev) => ({
                                ...prev,
                                description: e.target.value,
                              }))
                            }
                            onKeyDown={(e) => handleEditKeyDown(e, row.id)}
                            className="w-full px-2 py-1 border border-blue-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 text-center"
                          />
                        ) : (
                          <span className="whitespace-pre-wrap">
                            {row.description || "—"}
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-sm whitespace-nowrap text-center border border-gray-300 align-middle">
                        <div
                          className={`inline-flex items-center justify-center gap-2 ${
                            isRTL ? "flex-row-reverse" : ""
                          }`}
                        >
                          {isEditing ? (
                            <>
                              <button
                                type="button"
                                onClick={() => saveEdit(row.id)}
                                disabled={saving}
                                className="inline-flex items-center px-2.5 py-1.5 text-xs font-medium text-white bg-blue-600 rounded hover:bg-blue-700 disabled:opacity-50"
                              >
                                {t("common.save")}
                              </button>
                              <button
                                type="button"
                                onClick={cancelEdit}
                                className="inline-flex items-center px-2.5 py-1.5 text-xs font-medium text-gray-700 bg-gray-100 rounded hover:bg-gray-200"
                              >
                                {t("common.cancel")}
                              </button>
                            </>
                          ) : (
                            <>
                              <button
                                type="button"
                                onClick={() => startEdit(row)}
                                className={`inline-flex items-center px-2.5 py-1.5 text-xs font-medium text-blue-700 bg-blue-50 rounded hover:bg-blue-100 ${
                                  isRTL ? "flex-row-reverse" : ""
                                }`}
                              >
                                <Pencil
                                  className={`h-3.5 w-3.5 ${
                                    isRTL ? "ml-1" : "mr-1"
                                  }`}
                                />
                                {t("common.edit")}
                              </button>
                              <button
                                type="button"
                                onClick={() => handleDelete(row)}
                                className={`inline-flex items-center px-2.5 py-1.5 text-xs font-medium text-red-700 bg-red-50 rounded hover:bg-red-100 ${
                                  isRTL ? "flex-row-reverse" : ""
                                }`}
                              >
                                <Trash2
                                  className={`h-3.5 w-3.5 ${
                                    isRTL ? "ml-1" : "mr-1"
                                  }`}
                                />
                                {t("common.delete")}
                              </button>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default ProjectInfoFiles;
