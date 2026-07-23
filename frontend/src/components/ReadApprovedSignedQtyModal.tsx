import React, { useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { FileText, Upload, X } from "lucide-react";
import toast from "react-hot-toast";
import { importApi } from "../services/api";
import { ApprovedSignedQtyImportResponse } from "../types";

interface ReadApprovedSignedQtyModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: (result: ApprovedSignedQtyImportResponse) => void;
}

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

    setIsSubmitting(true);
    try {
      const result = await importApi.importApprovedSignedQty(selectedFile);
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

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-lg mx-4">
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
            disabled={isSubmitting || !selectedFile}
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
