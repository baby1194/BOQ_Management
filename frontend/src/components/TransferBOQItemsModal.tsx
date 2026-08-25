import React, { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { X } from "lucide-react";
import toast from "react-hot-toast";
import { boqApi } from "../services/api";
import { useProject } from "../contexts/ProjectContext";
import {
  BOQItem,
  BOQTransferPreviewResponse,
  BOQTransferResponse,
} from "../types";

interface TransferBOQItemsModalProps {
  isOpen: boolean;
  onClose: () => void;
  selectedItems: BOQItem[];
  onTransferred?: (result: BOQTransferResponse) => void;
}

const TransferBOQItemsModal: React.FC<TransferBOQItemsModalProps> = ({
  isOpen,
  onClose,
  selectedItems,
  onTransferred,
}) => {
  const { t } = useTranslation();
  const { projects, activeProjectId } = useProject();
  const [targetProjectId, setTargetProjectId] = useState("");
  const [preview, setPreview] = useState<BOQTransferPreviewResponse | null>(
    null
  );
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const targetProjects = useMemo(
    () => projects.filter((p) => p.id !== activeProjectId),
    [projects, activeProjectId]
  );

  const selectedIds = useMemo(
    () => selectedItems.map((item) => item.id),
    [selectedItems]
  );

  useEffect(() => {
    if (!isOpen) {
      setTargetProjectId("");
      setPreview(null);
      setPreviewError(null);
      setPreviewLoading(false);
      setIsSubmitting(false);
    }
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen || !targetProjectId || selectedIds.length === 0) {
      setPreview(null);
      setPreviewError(null);
      return;
    }

    let cancelled = false;
    const loadPreview = async () => {
      setPreviewLoading(true);
      setPreviewError(null);
      try {
        const result = await boqApi.transferPreview({
          target_project_id: targetProjectId,
          boq_item_ids: selectedIds,
        });
        if (!cancelled) {
          setPreview(result);
        }
      } catch (error: unknown) {
        if (!cancelled) {
          const message =
            (error as { response?: { data?: { detail?: string } } })?.response
              ?.data?.detail || t("boq.transferPreviewFailed");
          setPreview(null);
          setPreviewError(message);
        }
      } finally {
        if (!cancelled) {
          setPreviewLoading(false);
        }
      }
    };

    loadPreview();
    return () => {
      cancelled = true;
    };
  }, [isOpen, targetProjectId, selectedIds, t]);

  if (!isOpen) {
    return null;
  }

  const handleCopy = async () => {
    if (!targetProjectId || !preview || preview.copy_count === 0) {
      return;
    }
    setIsSubmitting(true);
    try {
      const result = await boqApi.transfer({
        target_project_id: targetProjectId,
        boq_item_ids: selectedIds,
      });
      if (result.skipped_count > 0 && result.transferred_count > 0) {
        toast.success(result.message);
      } else if (result.transferred_count > 0) {
        toast.success(result.message);
      } else {
        toast.error(result.message);
      }
      onTransferred?.(result);
      onClose();
    } catch (error: unknown) {
      const message =
        (error as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail || t("boq.transferFailed");
      toast.error(message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">
            {t("boq.transferTitle")}
          </h2>
          <button
            onClick={onClose}
            className="p-1 rounded-md text-gray-500 hover:bg-gray-100"
            aria-label={t("common.close")}
            disabled={isSubmitting}
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="px-6 py-4 space-y-4">
          <p className="text-sm text-gray-600">
            {t("boq.transferDescription", { count: selectedItems.length })}
          </p>

          <div>
            <label
              htmlFor="transfer-target-project"
              className="block text-sm font-medium text-gray-700 mb-2"
            >
              {t("boq.transferTargetProject")}
            </label>
            <select
              id="transfer-target-project"
              value={targetProjectId}
              onChange={(e) => setTargetProjectId(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              disabled={isSubmitting || targetProjects.length === 0}
            >
              <option value="">{t("boq.transferSelectProject")}</option>
              {targetProjects.map((project) => (
                <option key={project.id} value={project.id}>
                  {project.name}
                </option>
              ))}
            </select>
            {targetProjects.length === 0 && (
              <p className="text-sm text-amber-700 mt-2">
                {t("boq.transferNoOtherProjects")}
              </p>
            )}
          </div>

          {previewLoading && (
            <p className="text-sm text-gray-500">{t("boq.transferChecking")}</p>
          )}

          {previewError && (
            <div className="bg-red-50 border border-red-200 rounded-md p-3 text-sm text-red-700">
              {previewError}
            </div>
          )}

          {preview && !previewLoading && (
            <div className="space-y-3">
              {preview.conflict_count > 0 && (
                <div className="bg-amber-50 border border-amber-200 rounded-md p-3">
                  <p className="text-sm font-medium text-amber-900">
                    {t("boq.transferConflictsWarning", {
                      count: preview.conflict_count,
                    })}
                  </p>
                  <p className="text-xs text-amber-800 mt-1">
                    {t("boq.transferConflictsSkipNote")}
                  </p>
                  <ul className="mt-2 max-h-32 overflow-y-auto text-sm text-amber-900 list-disc list-inside space-y-1">
                    {preview.conflicts.map((item) => (
                      <li key={item.boq_item_id}>
                        <span className="font-mono">{item.section_number}</span>
                        {item.description
                          ? ` — ${item.description.slice(0, 80)}`
                          : ""}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {preview.copy_count > 0 ? (
                <div className="bg-green-50 border border-green-200 rounded-md p-3">
                  <p className="text-sm text-green-800">
                    {t("boq.transferWillCopy", { count: preview.copy_count })}
                  </p>
                </div>
              ) : (
                <div className="bg-gray-50 border border-gray-200 rounded-md p-3">
                  <p className="text-sm text-gray-700">
                    {t("boq.transferNothingToCopy")}
                  </p>
                </div>
              )}
            </div>
          )}
        </div>

        <div className="flex justify-end gap-3 px-6 py-4 border-t border-gray-200">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200"
            disabled={isSubmitting}
          >
            {t("common.cancel")}
          </button>
          <button
            type="button"
            onClick={handleCopy}
            disabled={
              isSubmitting ||
              previewLoading ||
              !targetProjectId ||
              !preview ||
              preview.copy_count === 0
            }
            className="px-4 py-2 text-white bg-teal-600 rounded-md hover:bg-teal-700 focus:outline-none focus:ring-2 focus:ring-teal-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSubmitting
              ? t("boq.transferCopying")
              : preview?.conflict_count
              ? t("boq.transferCopyNonConflicting")
              : t("boq.transferCopy")}
          </button>
        </div>
      </div>
    </div>
  );
};

export default TransferBOQItemsModal;
