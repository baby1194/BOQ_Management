import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { X } from "lucide-react";
import { useProject } from "../contexts/ProjectContext";
import toast from "react-hot-toast";

interface NewProjectModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const NewProjectModal: React.FC<NewProjectModalProps> = ({
  isOpen,
  onClose,
}) => {
  const { t } = useTranslation();
  const { createProject } = useProject();
  const [name, setName] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen) {
    return null;
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = name.trim();
    if (!trimmed) {
      return;
    }

    setIsSubmitting(true);
    try {
      await createProject(trimmed);
      toast.success(t("projects.created"));
      setName("");
      onClose();
    } catch (error: unknown) {
      const message =
        (error as { response?: { data?: { detail?: string } } })?.response
          ?.data?.detail || t("projects.createFailed");
      toast.error(message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md mx-4">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">
            {t("projects.newProject")}
          </h2>
          <button
            onClick={onClose}
            className="p-1 rounded-md text-gray-500 hover:bg-gray-100"
            aria-label={t("common.close")}
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="px-6 py-4">
          <label
            htmlFor="project-name"
            className="block text-sm font-medium text-gray-700 mb-2"
          >
            {t("projects.name")}
          </label>
          <input
            id="project-name"
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder={t("projects.namePlaceholder")}
            autoFocus
            disabled={isSubmitting}
          />

          <div className="flex justify-end gap-3 mt-6">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200"
              disabled={isSubmitting}
            >
              {t("common.cancel")}
            </button>
            <button
              type="submit"
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50"
              disabled={isSubmitting || !name.trim()}
            >
              {isSubmitting ? t("common.loading") : t("common.create")}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default NewProjectModal;
