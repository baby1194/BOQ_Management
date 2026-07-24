import React from "react";
import { useTranslation } from "react-i18next";
import { FileText, Paperclip, Trash2 } from "lucide-react";

interface ConcentrationDrawingFilesCellProps {
  drawingFiles: string[];
  isRTL: boolean;
  isUploading: boolean;
  isExpanded: boolean;
  isDeletingAll?: boolean;
  onAttach: () => void;
  onOpen: (path: string) => void;
  onRemove: (path: string) => void;
  onRemoveAll?: () => void;
  onToggleExpanded: () => void;
  drawingFileName: (path: string) => string;
}

const ConcentrationDrawingFilesCell: React.FC<
  ConcentrationDrawingFilesCellProps
> = ({
  drawingFiles,
  isRTL,
  isUploading,
  isExpanded,
  isDeletingAll = false,
  onAttach,
  onOpen,
  onRemove,
  onRemoveAll,
  onToggleExpanded,
  drawingFileName,
}) => {
  const { t } = useTranslation();
  const showToggle = drawingFiles.length > 1;
  const showDeleteAll = drawingFiles.length > 1 && !!onRemoveAll;

  const renderDrawingFile = (filePath: string) => (
    <div
      key={filePath}
      className={`flex items-center gap-1 rounded bg-gray-50 border border-gray-200 px-2 py-1 min-w-0 ${
        isRTL ? "flex-row-reverse" : ""
      }`}
    >
      <FileText className="h-3.5 w-3.5 shrink-0 text-gray-400" />
      <button
        type="button"
        onClick={() => onOpen(filePath)}
        onDoubleClick={(e) => e.stopPropagation()}
        className="flex-1 min-w-0 text-blue-600 hover:text-blue-800 hover:underline truncate text-xs text-left"
        title={filePath}
      >
        {drawingFileName(filePath)}
      </button>
      <button
        type="button"
        onClick={() => onRemove(filePath)}
        onDoubleClick={(e) => e.stopPropagation()}
        className="shrink-0 text-red-500 hover:text-red-700 text-sm leading-none px-0.5"
        title={t("concentration.removeDrawing")}
        aria-label={t("concentration.removeDrawing")}
      >
        ×
      </button>
    </div>
  );

  const deleteAllButton = showDeleteAll ? (
    <button
      type="button"
      onClick={onRemoveAll}
      onDoubleClick={(e) => e.stopPropagation()}
      disabled={isUploading || isDeletingAll}
      className="inline-flex items-center justify-center gap-1 bg-red-600 text-white px-2 py-1 rounded-md text-xs font-medium hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors shrink-0 whitespace-nowrap"
      title={t("concentration.deleteAllDrawingsTitle")}
    >
      <Trash2 className="h-3.5 w-3.5" />
      <span>
        {isDeletingAll
          ? t("concentration.deletingAllDrawings")
          : t("concentration.deleteAllDrawings")}
      </span>
    </button>
  ) : null;

  const attachButton = (
    <button
      type="button"
      onClick={onAttach}
      onDoubleClick={(e) => e.stopPropagation()}
      disabled={isUploading || isDeletingAll}
      className="inline-flex items-center justify-center gap-1 bg-indigo-600 text-white px-2 py-1 rounded-md text-xs font-medium hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors shrink-0 whitespace-nowrap"
    >
      <Paperclip className="h-3.5 w-3.5" />
      <span>
        {isUploading
          ? t("concentration.uploadingDrawings")
          : t("concentration.attachDrawings")}
      </span>
    </button>
  );

  if (drawingFiles.length === 0) {
    return (
      <div className="flex flex-col items-stretch justify-center gap-2 min-h-[2.5rem]">
        <div className="flex justify-center w-full">{attachButton}</div>
      </div>
    );
  }

  if (!isExpanded) {
    return (
      <div className="flex flex-col items-stretch justify-center gap-2 min-h-[2.5rem]">
        <div
          className={`flex items-center gap-1 w-full min-w-0 ${
            isRTL ? "flex-row-reverse" : ""
          }`}
        >
          <div className="flex-1 min-w-0">
            {renderDrawingFile(drawingFiles[0])}
          </div>
          {showToggle && (
            <button
              type="button"
              onClick={onToggleExpanded}
              onDoubleClick={(e) => e.stopPropagation()}
              className="shrink-0 text-xs font-medium px-2 py-1 rounded border bg-sky-100 text-sky-800 border-sky-200 hover:bg-sky-100 whitespace-nowrap"
            >
              {t("concentration.showMoreDrawings")}
            </button>
          )}
          {deleteAllButton}
          {attachButton}
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-stretch justify-center gap-2 min-h-[2.5rem]">
      <div className="w-full space-y-1">
        {drawingFiles.map((filePath) => renderDrawingFile(filePath))}
        <button
          type="button"
          onClick={onToggleExpanded}
          onDoubleClick={(e) => e.stopPropagation()}
          className="w-full text-xs font-medium px-2 py-1 rounded border transition-colors bg-amber-100 text-amber-800 border-amber-200 hover:bg-amber-100"
        >
          {t("concentration.showLessDrawings")}
        </button>
      </div>
      <div
        className={`flex justify-center gap-1 ${
          isRTL ? "flex-row-reverse" : ""
        }`}
      >
        {deleteAllButton}
        {attachButton}
      </div>
    </div>
  );
};

export default ConcentrationDrawingFilesCell;
