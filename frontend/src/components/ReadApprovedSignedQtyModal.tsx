import React, { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { FileText, Upload, X } from "lucide-react";
import toast from "react-hot-toast";
import { importApi } from "../services/api";
import { ApprovedSignedQtyImportResponse } from "../types";
import { getProjectItem, setProjectItem } from "../utils/localStorage";

interface ReadApprovedSignedQtyModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: (result: ApprovedSignedQtyImportResponse) => void;
}

const PREFS_KEY = "approved-signed-qty-pdf-prefs";

interface ApprovedSignedQtyPrefs {
  sectionColumnName: string;
  qtyColumnName: string;
  structure: string;
}

const DEFAULT_PREFS: ApprovedSignedQtyPrefs = {
  sectionColumnName: 'מק"ט',
  qtyColumnName: "כמות מצטברת לחשבון נוכחי",
  structure: "",
};

const loadPrefs = (): ApprovedSignedQtyPrefs => {
  const saved = getProjectItem(PREFS_KEY);
  if (!saved) {
    return { ...DEFAULT_PREFS };
  }
  try {
    const parsed = JSON.parse(saved) as Partial<ApprovedSignedQtyPrefs>;
    return {
      sectionColumnName:
        typeof parsed.sectionColumnName === "string"
          ? parsed.sectionColumnName
          : DEFAULT_PREFS.sectionColumnName,
      qtyColumnName:
        typeof parsed.qtyColumnName === "string"
          ? parsed.qtyColumnName
          : DEFAULT_PREFS.qtyColumnName,
      structure:
        typeof parsed.structure === "string"
          ? parsed.structure
          : DEFAULT_PREFS.structure,
    };
  } catch {
    return { ...DEFAULT_PREFS };
  }
};

const ReadApprovedSignedQtyModal: React.FC<ReadApprovedSignedQtyModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
}) => {
  const { t } = useTranslation();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [sectionColumnName, setSectionColumnName] = useState(
    DEFAULT_PREFS.sectionColumnName,
  );
  const [qtyColumnName, setQtyColumnName] = useState(
    DEFAULT_PREFS.qtyColumnName,
  );
  const [structure, setStructure] = useState(DEFAULT_PREFS.structure);

  useEffect(() => {
    if (!isOpen) {
      return;
    }
    const prefs = loadPrefs();
    setSectionColumnName(prefs.sectionColumnName);
    setQtyColumnName(prefs.qtyColumnName);
    setStructure(prefs.structure);
  }, [isOpen]);

  if (!isOpen) {
    return null;
  }

  const resetAndClose = () => {
    setSelectedFile(null);
    setIsDragging(false);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
    onClose();
  };

  const acceptPdf = (file: File) => {
    const isPdf =
      file.type === "application/pdf" ||
      file.name.toLowerCase().endsWith(".pdf");
    if (!isPdf) {
      toast.error(t("dashboard.selectValidPdf"));
      return;
    }
    setSelectedFile(file);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      acceptPdf(files[0]);
    }
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      acceptPdf(files[0]);
    }
  };

  const handleSubmit = async () => {
    if (!selectedFile) {
      toast.error(t("dashboard.selectPdfFirst"));
      return;
    }
    const trimmedSection = sectionColumnName.trim();
    const trimmedQty = qtyColumnName.trim();
    if (!trimmedSection) {
      toast.error(t("dashboard.sectionColumnNameRequired"));
      return;
    }
    if (!trimmedQty) {
      toast.error(t("dashboard.qtyColumnNameRequired"));
      return;
    }

    const trimmedStructure = structure.trim();
    setProjectItem(
      PREFS_KEY,
      JSON.stringify({
        sectionColumnName: trimmedSection,
        qtyColumnName: trimmedQty,
        structure: trimmedStructure,
      }),
    );

    setIsSubmitting(true);
    try {
      const result = await importApi.importApprovedSignedQty(selectedFile, {
        sectionColumnName: trimmedSection,
        qtyColumnName: trimmedQty,
        structure: trimmedStructure,
      });
      if (result.success) {
        let message = t("dashboard.approvedSignedQtyUpdated", {
          count: result.items_updated,
        });
        if (result.items_unchanged > 0) {
          message += ` (${result.items_unchanged} ${t("dashboard.itemsAlreadyUpToDate")})`;
        }
        if (result.items_not_found > 0) {
          message += ` (${result.items_not_found} ${t("dashboard.itemsNotFoundInBoq")})`;
        }
        toast.success(message);
        onSuccess?.(result);
        resetAndClose();
      } else {
        toast.error(
          result.message || t("dashboard.approvedSignedQtyImportFailed"),
        );
      }
    } catch (error: unknown) {
      const message =
        (error as { response?: { data?: { detail?: string } } })?.response
          ?.data?.detail || t("dashboard.approvedSignedQtyImportFailed");
      toast.error(message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const exampleSection = structure.trim()
    ? `${structure.trim().replace(/^\.+|\.+$/g, "")}.02.01.0010`
    : "02.01.0010";

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">
            {t("dashboard.readApprovedSignedQty")}
          </h2>
          <button
            type="button"
            onClick={resetAndClose}
            className="p-1 rounded-md text-gray-500 hover:bg-gray-100"
            aria-label={t("common.close")}
            disabled={isSubmitting}
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="px-6 py-4 space-y-4">
          <p className="text-sm text-gray-600">
            {t("dashboard.readApprovedSignedQtyDescription")}
          </p>

          <div className="space-y-3">
            <div>
              <label
                htmlFor="section-column-name"
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                {t("dashboard.sectionColumnName")}
              </label>
              <input
                id="section-column-name"
                type="text"
                value={sectionColumnName}
                onChange={(e) => setSectionColumnName(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder='מק"ט'
                disabled={isSubmitting}
              />
            </div>

            <div>
              <label
                htmlFor="qty-column-name"
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                {t("dashboard.qtyColumnName")}
              </label>
              <input
                id="qty-column-name"
                type="text"
                value={qtyColumnName}
                onChange={(e) => setQtyColumnName(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="כמות מצטברת לחשבון נוכחי"
                disabled={isSubmitting}
              />
            </div>

            <div>
              <label
                htmlFor="structure-prefix"
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                {t("dashboard.structurePrefix")}
              </label>
              <input
                id="structure-prefix"
                type="text"
                value={structure}
                onChange={(e) => setStructure(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="1"
                disabled={isSubmitting}
              />
              <p className="mt-1 text-xs text-gray-500">
                {t("dashboard.structurePrefixHint", {
                  example: exampleSection,
                })}
              </p>
            </div>
          </div>

          <div
            onDragOver={(e) => {
              e.preventDefault();
              setIsDragging(true);
            }}
            onDragLeave={(e) => {
              e.preventDefault();
              setIsDragging(false);
            }}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
              isDragging
                ? "border-blue-500 bg-blue-50"
                : "border-gray-300 hover:border-blue-400 hover:bg-gray-50"
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,application/pdf"
              className="hidden"
              onChange={handleFileInput}
              disabled={isSubmitting}
            />
            {selectedFile ? (
              <div className="flex flex-col items-center gap-2">
                <FileText className="h-10 w-10 text-blue-600" />
                <p className="font-medium text-gray-900">{selectedFile.name}</p>
                <p className="text-xs text-gray-500">
                  {(selectedFile.size / 1024).toFixed(1)} KB
                </p>
                <p className="text-sm text-blue-600">
                  {t("dashboard.clickOrDropToChangeFile")}
                </p>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-2">
                <Upload className="h-10 w-10 text-gray-400" />
                <p className="font-medium text-gray-900">
                  {t("dashboard.openFileModal")}
                </p>
                <p className="text-sm text-gray-500">
                  {t("dashboard.dropPdfHere")}
                </p>
              </div>
            )}
          </div>
        </div>

        <div className="flex justify-end gap-3 px-6 py-4 border-t border-gray-200">
          <button
            type="button"
            onClick={resetAndClose}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200"
            disabled={isSubmitting}
          >
            {t("common.cancel")}
          </button>
          <button
            type="button"
            onClick={handleSubmit}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50"
            disabled={
              isSubmitting ||
              !selectedFile ||
              !sectionColumnName.trim() ||
              !qtyColumnName.trim()
            }
          >
            {isSubmitting
              ? t("dashboard.readingApprovedSignedQty")
              : t("dashboard.updateApprovedSignedQty")}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ReadApprovedSignedQtyModal;
