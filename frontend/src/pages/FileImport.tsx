import React, { useState } from "react";
import { useMutation, useQueryClient } from "react-query";
import { useTranslation } from "react-i18next";
import { useLanguage } from "../contexts/LanguageContext";
import { importApi } from "../services/api";
import { CalculationImportResponse } from "../types";
import {
  Upload,
  FileText,
  AlertCircle,
  CheckCircle,
  X,
  FolderOpen,
  FileSpreadsheet,
} from "lucide-react";
import toast from "react-hot-toast";

const FileImport: React.FC = () => {
  const { t } = useTranslation();
  const { isRTL } = useLanguage();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedFolder, setSelectedFolder] = useState<FileList | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isDraggingFolder, setIsDraggingFolder] = useState(false);
  const [importResult, setImportResult] = useState<any>(null);
  const [calculationImportResult, setCalculationImportResult] =
    useState<CalculationImportResponse | null>(null);
  const queryClient = useQueryClient();

  const importMutation = useMutation(importApi.importBOQ, {
    onSuccess: (data) => {
      setImportResult(data);
      toast.success(t("import.boqImportTitle") + " " + t("common.success"));
      // Refresh the dashboard data
      queryClient.invalidateQueries("boq-items");
      queryClient.invalidateQueries("summary");
    },
    onError: (error: any) => {
      toast.error(
        error.response?.data?.detail ||
          t("import.title") + " " + t("common.error")
      );
    },
  });

  const calculationImportMutation = useMutation(
    importApi.importCalculationSheets,
    {
      onSuccess: (data) => {
        setCalculationImportResult(data);
        toast.success(t("import.calculationSheetsImported"));
        // Refresh the calculation sheets data
        queryClient.invalidateQueries("calculation-sheets");

        // Show notification about populating calculation sheets
        setTimeout(() => {
          toast.success(t("import.populationReminder"), {
            duration: 8000,
          });
        }, 1000);
      },
      onError: (error: any) => {
        toast.error(
          error.response?.data?.detail ||
            t("import.failedToImportCalculationSheets")
        );
      },
    }
  );

  const handleFileSelect = (file: File) => {
    if (
      file.type ===
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" ||
      file.type === "application/vnd.ms-excel"
    ) {
      setSelectedFile(file);
      setImportResult(null);
    } else {
      toast.error(t("import.selectValidExcel"));
    }
  };

  const handleFolderSelect = (files: FileList) => {
    const excelFiles = Array.from(files).filter(
      (file) =>
        file.type ===
          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" ||
        file.type === "application/vnd.ms-excel"
    );

    if (excelFiles.length === 0) {
      toast.error(t("import.noValidExcelFiles"));
      return;
    }

    setSelectedFolder(files);
    setCalculationImportResult(null);
    toast.success(t("import.foundExcelFiles", { count: excelFiles.length }));
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      handleFileSelect(files[0]);
    }
  };

  const handleFolderDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDraggingFolder(true);
  };

  const handleFolderDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDraggingFolder(false);
  };

  const handleFolderDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDraggingFolder(false);

    const files = e.dataTransfer.files;
    if (files.length > 0) {
      handleFolderSelect(files);
    }
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      handleFileSelect(files[0]);
    }
  };

  const handleFolderInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      handleFolderSelect(files);
    }
  };

  const handleImport = () => {
    if (selectedFile) {
      importMutation.mutate(selectedFile);
    }
  };

  const handleCalculationImport = () => {
    if (selectedFolder) {
      const formData = new FormData();
      Array.from(selectedFolder).forEach((file, index) => {
        formData.append(`files`, file);
      });
      calculationImportMutation.mutate(formData);
    }
  };

  const clearFile = () => {
    setSelectedFile(null);
    setImportResult(null);
  };

  const clearFolder = () => {
    setSelectedFolder(null);
    setCalculationImportResult(null);
  };

  const getExcelFilesCount = () => {
    if (!selectedFolder) return 0;
    return Array.from(selectedFolder).filter(
      (file) =>
        file.type ===
          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" ||
        file.type === "application/vnd.ms-excel"
    ).length;
  };

  return (
    <div className="space-y-6" dir={isRTL ? "rtl" : "ltr"}>
      <div>
        <h1 className="text-3xl font-bold text-gray-900">
          {t("import.title")}
        </h1>
        <p className="mt-2 text-gray-600">{t("import.subtitle")}</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Left Side - BOQ File Import */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="space-y-4">
            <div>
              <h2 className="text-lg font-semibold text-gray-900 mb-2">
                {t("import.boqImportSection")}
              </h2>
              <p className="text-sm text-gray-600">
                {t("import.boqImportDescription")}
              </p>
            </div>

            {/* Drag & Drop Area */}
            <div
              className={`border-2 border-dashed rounded-lg p-6 text-center transition-colors ${
                isDragging
                  ? "border-blue-500 bg-blue-50"
                  : "border-gray-300 hover:border-gray-400"
              }`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
            >
              {selectedFile ? (
                <div className="space-y-4">
                  <div className="flex items-center justify-center">
                    <FileText className="h-12 w-12 text-green-500" />
                  </div>
                  <div>
                    <p className="text-lg font-medium text-gray-900">
                      {selectedFile.name}
                    </p>
                    <p className="text-sm text-gray-500">
                      {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                    </p>
                  </div>
                  <div className="flex items-center justify-center space-x-2">
                    <button
                      onClick={handleImport}
                      disabled={importMutation.isLoading}
                      className="btn btn-primary btn-md"
                    >
                      {importMutation.isLoading ? (
                        <div className="flex items-center">
                          <div
                            className={`animate-spin rounded-full h-4 w-4 border-b-2 border-white ${
                              isRTL ? "ml-2" : "mr-2"
                            }`}
                          ></div>
                          {t("import.importing")}
                        </div>
                      ) : (
                        <div className="flex items-center">
                          <Upload
                            className={`h-4 w-4 ${isRTL ? "ml-2" : "mr-2"}`}
                          />
                          {t("import.importFile")}
                        </div>
                      )}
                    </button>
                    <button
                      onClick={clearFile}
                      className="btn btn-outline btn-md"
                    >
                      <X className={`h-4 w-4 ${isRTL ? "ml-2" : "mr-2"}`} />
                      {t("import.clear")}
                    </button>
                  </div>
                </div>
              ) : (
                <div className="space-y-4">
                  <Upload className="h-12 w-12 text-gray-400 mx-auto" />
                  <div>
                    <p className="text-lg font-medium text-gray-900">
                      {t("import.dropBoqFileHere")}
                    </p>
                    <p className="text-sm text-gray-500">
                      {t("import.orClickToBrowse")}
                    </p>
                  </div>
                  <input
                    type="file"
                    accept=".xlsx,.xls"
                    onChange={handleFileInput}
                    className="hidden"
                    id="boq-file-input"
                  />
                  <label
                    htmlFor="boq-file-input"
                    className="btn btn-primary btn-md cursor-pointer"
                  >
                    <Upload className={`h-4 w-4 ${isRTL ? "ml-2" : "mr-2"}`} />
                    {t("import.chooseFile")}
                  </label>
                </div>
              )}
            </div>
          </div>

          {/* BOQ Import Results */}
          {importResult && (
            <div className="mt-6 space-y-4">
              <h3 className="text-md font-semibold text-gray-900">
                {t("import.importResults")}
              </h3>

              <div
                className={`flex items-center p-4 rounded-lg ${
                  importResult.success
                    ? "bg-green-50 border border-green-200"
                    : "bg-red-50 border border-red-200"
                }`}
              >
                {importResult.success ? (
                  <CheckCircle
                    className={`h-5 w-5 text-green-500 ${
                      isRTL ? "ml-3" : "mr-3"
                    }`}
                  />
                ) : (
                  <AlertCircle
                    className={`h-5 w-5 text-red-500 ${
                      isRTL ? "ml-3" : "mr-3"
                    }`}
                  />
                )}
                <div>
                  <p
                    className={`font-medium ${
                      importResult.success ? "text-green-800" : "text-red-800"
                    }`}
                  >
                    {importResult.success
                      ? t("auth.importSuccessful")
                      : t("auth.importFailed")}
                  </p>
                  <p
                    className={`text-sm ${
                      importResult.success ? "text-green-600" : "text-red-600"
                    }`}
                  >
                    {importResult.message}
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="bg-gray-50 p-3 rounded-lg">
                  <p className="text-sm font-medium text-gray-600">
                    {t("auth.filesProcessed")}
                  </p>
                  <p className="text-xl font-bold text-gray-900">
                    {importResult.files_processed}
                  </p>
                </div>
                <div className="bg-gray-50 p-3 rounded-lg">
                  <p className="text-sm font-medium text-gray-600">
                    {t("auth.itemsImported")}
                  </p>
                  <p className="text-xl font-bold text-gray-900">
                    {importResult.items_updated}
                  </p>
                </div>
              </div>

              {/* Show errors/warnings */}
              {importResult.errors && importResult.errors.length > 0 && (
                <div className="mt-4">
                  <h4 className="text-sm font-medium text-gray-700 mb-2">
                    {t("import.importDetails")}
                  </h4>
                  <div className="space-y-2 max-h-40 overflow-y-auto">
                    {importResult.errors.map((error, index) => (
                      <div
                        key={index}
                        className={`text-xs p-2 rounded ${
                          error.includes("skipped") || error.includes("Skipped")
                            ? "bg-yellow-50 text-yellow-800 border border-yellow-200"
                            : "bg-red-50 text-red-800 border border-red-200"
                        }`}
                      >
                        {error}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Right Side - Calculation Sheets Import */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="space-y-4">
            <div>
              <h2 className="text-lg font-semibold text-gray-900 mb-2">
                {t("import.calculationSheetsSection")}
              </h2>
              <p className="text-sm text-gray-600">
                {t("import.calculationSheetsDescription")}
              </p>
            </div>

            {/* Drag & Drop Area */}
            <div
              className={`border-2 border-dashed rounded-lg p-6 text-center transition-colors ${
                isDraggingFolder
                  ? "border-green-500 bg-green-50"
                  : "border-gray-300 hover:border-gray-400"
              }`}
              onDragOver={handleFolderDragOver}
              onDragLeave={handleFolderDragLeave}
              onDrop={handleFolderDrop}
            >
              {selectedFolder ? (
                <div className="space-y-4">
                  <div className="flex items-center justify-center">
                    <FolderOpen className="h-12 w-12 text-green-500" />
                  </div>
                  <div>
                    <p className="text-lg font-medium text-gray-900">
                      {t("import.folderSelected")}
                    </p>
                    <p className="text-sm text-gray-500">
                      {t("import.excelFilesFound", {
                        count: getExcelFilesCount(),
                      })}
                    </p>
                    <div className="mt-2 text-xs text-gray-400 max-h-20 overflow-y-auto">
                      {Array.from(selectedFolder)
                        .slice(0, 5)
                        .map((file, index) => (
                          <div
                            key={index}
                            className="flex items-center justify-center"
                          >
                            <FileSpreadsheet
                              className={`h-3 w-3 ${isRTL ? "ml-1" : "mr-1"}`}
                            />
                            {file.name}
                          </div>
                        ))}
                      {selectedFolder.length > 5 && (
                        <div className="text-gray-400">
                          ... {t("import.andMore")} {selectedFolder.length - 5}
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center justify-center space-x-2">
                    <button
                      onClick={handleCalculationImport}
                      disabled={calculationImportMutation.isLoading}
                      className="btn btn-success btn-md"
                    >
                      {calculationImportMutation.isLoading ? (
                        <div className="flex items-center">
                          <div
                            className={`animate-spin rounded-full h-4 w-4 border-b-2 border-white ${
                              isRTL ? "ml-2" : "mr-2"
                            }`}
                          ></div>
                          {t("import.importing")}
                        </div>
                      ) : (
                        <div className="flex items-center">
                          <Upload
                            className={`h-4 w-4 ${isRTL ? "ml-2" : "mr-2"}`}
                          />
                          {t("import.importSheets")}
                        </div>
                      )}
                    </button>
                    <button
                      onClick={clearFolder}
                      className="btn btn-outline btn-md"
                    >
                      <X className={`h-4 w-4 ${isRTL ? "ml-2" : "mr-2"}`} />
                      {t("import.clear")}
                    </button>
                  </div>
                </div>
              ) : (
                <div className="space-y-4">
                  <FolderOpen className="h-12 w-12 text-gray-400 mx-auto" />
                  <div>
                    <p className="text-lg font-medium text-gray-900">
                      {t("import.dropCalculationSheetsFolder")}
                    </p>
                    <p className="text-sm text-gray-500">
                      {t("import.orClickToBrowseFolder")}
                    </p>
                  </div>
                  <input
                    type="file"
                    multiple
                    accept=".xlsx,.xls"
                    onChange={handleFolderInput}
                    className="hidden"
                    id="calculation-folder-input"
                  />
                  <label
                    htmlFor="calculation-folder-input"
                    className="btn btn-success btn-md cursor-pointer"
                  >
                    <FolderOpen
                      className={`h-4 w-4 ${isRTL ? "ml-2" : "mr-2"}`}
                    />
                    {t("import.chooseFolder")}
                  </label>
                </div>
              )}
            </div>
          </div>

          {/* Calculation Sheets Import Results */}
          {calculationImportResult && (
            <div className="mt-6 space-y-4">
              <h3 className="text-md font-semibold text-gray-900">
                {t("import.importResults")}
              </h3>

              <div
                className={`flex items-center p-4 rounded-lg ${
                  calculationImportResult.success
                    ? "bg-green-50 border border-green-200"
                    : "bg-red-50 border border-red-200"
                }`}
              >
                {calculationImportResult.success ? (
                  <CheckCircle
                    className={`h-5 w-5 text-green-500 ${
                      isRTL ? "ml-3" : "mr-3"
                    }`}
                  />
                ) : (
                  <AlertCircle
                    className={`h-5 w-5 text-red-500 ${
                      isRTL ? "ml-3" : "mr-3"
                    }`}
                  />
                )}
                <div>
                  <p
                    className={`font-medium ${
                      calculationImportResult.success
                        ? "text-green-800"
                        : "text-red-800"
                    }`}
                  >
                    {t(
                      calculationImportResult.success
                        ? "import.importSuccessful"
                        : "import.importFailed"
                    )}
                  </p>
                  <p
                    className={`text-sm ${
                      calculationImportResult.success
                        ? "text-green-600"
                        : "text-red-600"
                    }`}
                  >
                    {calculationImportResult.message}
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-4">
                <div className="bg-gray-50 p-3 rounded-lg">
                  <p className="text-sm font-medium text-gray-600">
                    {t("import.filesProcessed")}
                  </p>
                  <p className="text-xl font-bold text-gray-900">
                    {calculationImportResult.files_processed || 0}
                  </p>
                </div>
                <div className="bg-gray-50 p-3 rounded-lg">
                  <p className="text-sm font-medium text-gray-600">
                    {t("import.sheetsImported")}
                  </p>
                  <p className="text-xl font-bold text-gray-900">
                    {calculationImportResult.sheets_imported || 0}
                  </p>
                </div>
                <div className="bg-gray-50 p-3 rounded-lg">
                  <p className="text-sm font-medium text-gray-600">
                    {t("import.entriesImported")}
                  </p>
                  <p className="text-xl font-bold text-gray-900">
                    {calculationImportResult.entries_imported || 0}
                  </p>
                </div>
              </div>

              {/* Show detailed errors including skipped duplicates */}
              {calculationImportResult.errors &&
                calculationImportResult.errors.length > 0 && (
                  <div className="mt-4">
                    <h4 className="text-sm font-medium text-gray-700 mb-2">
                      {t("import.importDetails")}
                    </h4>
                    <div className="space-y-2 max-h-40 overflow-y-auto">
                      {calculationImportResult.errors.map((error, index) => (
                        <div
                          key={index}
                          className={`text-xs p-2 rounded ${
                            error.includes("Skipped:")
                              ? "bg-yellow-50 text-yellow-800 border border-yellow-200"
                              : "bg-red-50 text-red-800 border border-red-200"
                          }`}
                        >
                          {error}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default FileImport;
