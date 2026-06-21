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
  FileSpreadsheet,
} from "lucide-react";
import toast from "react-hot-toast";

const FileImport: React.FC = () => {
  const { t } = useTranslation();
  const { isRTL } = useLanguage();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [importResult, setImportResult] = useState<any>(null);
  const [boqSystemPassword, setBoqSystemPassword] = useState("");
  const [calculationSheetsPath, setCalculationSheetsPath] = useState("");
  const [listedCalculationFiles, setListedCalculationFiles] = useState<
    string[]
  >([]);
  const [readingCalculationFiles, setReadingCalculationFiles] = useState(false);
  const [calculationImportResult, setCalculationImportResult] =
    useState<CalculationImportResponse | null>(null);
  const queryClient = useQueryClient();

  const importMutation = useMutation(
    ({ file, systemPassword }: { file: File; systemPassword: string }) =>
      importApi.importBOQ(file, systemPassword),
    {
      onSuccess: (data) => {
        setImportResult(data);
        toast.success(t("import.boqImportTitle") + " " + t("common.success"));
        queryClient.invalidateQueries("boq-items");
        queryClient.invalidateQueries("summary");
      },
      onError: (error: any) => {
        if (error.response?.status === 403) {
          toast.error(t("boq.passwordIncorrect"));
          return;
        }
        toast.error(
          error.response?.data?.detail ||
            t("import.title") + " " + t("common.error")
        );
      },
    }
  );

  const calculationImportMutation = useMutation(
    importApi.importCalculationSheetsFromPaths,
    {
      onSuccess: (data) => {
        setCalculationImportResult(data);
        toast.success(t("import.calculationSheetsImported"));
        queryClient.invalidateQueries("calculation-sheets");

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
      setBoqSystemPassword("");
    } else {
      toast.error(t("import.selectValidExcel"));
    }
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

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      handleFileSelect(files[0]);
    }
  };

  const handleImport = () => {
    if (!selectedFile) return;
    const pwd = boqSystemPassword.trim();
    if (!pwd) {
      toast.error(t("import.systemPasswordRequiredForBOQ"));
      return;
    }
    importMutation.mutate({ file: selectedFile, systemPassword: pwd });
  };

  const handleReadCalculationFiles = async () => {
    const path = calculationSheetsPath.trim();
    if (!path) {
      toast.error(t("import.calculationSheetsPathRequired"));
      return;
    }

    try {
      setReadingCalculationFiles(true);
      setCalculationImportResult(null);
      const response = await importApi.listCalculationSheetFiles(path);
      setListedCalculationFiles(response.files);
      toast.success(
        t("import.foundExcelFiles", { count: response.files.length })
      );
    } catch (error: any) {
      toast.error(
        error.response?.data?.detail || t("import.failedToReadCalculationFiles")
      );
    } finally {
      setReadingCalculationFiles(false);
    }
  };

  const handleRemoveListedFile = (filePath: string) => {
    setListedCalculationFiles((prev) =>
      prev.filter((path) => path !== filePath)
    );
  };

  const handleCalculationImport = () => {
    if (listedCalculationFiles.length === 0) return;
    calculationImportMutation.mutate(listedCalculationFiles);
  };

  const clearFile = () => {
    setSelectedFile(null);
    setImportResult(null);
    setBoqSystemPassword("");
  };

  const clearCalculationFiles = () => {
    setListedCalculationFiles([]);
    setCalculationImportResult(null);
  };

  const getFileDisplayName = (filePath: string) => {
    const parts = filePath.split(/[/\\]/);
    return parts[parts.length - 1] || filePath;
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
                  <div className="w-full max-w-sm mx-auto space-y-3">
                    <div className="text-start">
                      <label
                        htmlFor="boq-system-password"
                        className="block text-sm font-medium text-gray-700 mb-1"
                      >
                        {t("auth.systemPassword")}
                      </label>
                      <input
                        id="boq-system-password"
                        type="password"
                        autoComplete="off"
                        value={boqSystemPassword}
                        onChange={(e) => setBoqSystemPassword(e.target.value)}
                        placeholder={t("boq.enterSystemPassword")}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      />
                      <p className="mt-1 text-xs text-gray-500">
                        {t("import.systemPasswordForBOQUpload")}
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

            <div className="space-y-3">
              <label
                htmlFor="calculation-sheets-path"
                className="block text-sm font-medium text-gray-700"
              >
                {t("import.calculationSheetsPath")}
              </label>
              <div className="flex gap-2">
                <input
                  id="calculation-sheets-path"
                  type="text"
                  value={calculationSheetsPath}
                  onChange={(e) => setCalculationSheetsPath(e.target.value)}
                  placeholder={t("import.calculationSheetsPathPlaceholder")}
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
                />
                <button
                  onClick={handleReadCalculationFiles}
                  disabled={readingCalculationFiles}
                  className="btn btn-success btn-md whitespace-nowrap"
                >
                  {readingCalculationFiles ? (
                    <div className="flex items-center">
                      <div
                        className={`animate-spin rounded-full h-4 w-4 border-b-2 border-white ${
                          isRTL ? "ml-2" : "mr-2"
                        }`}
                      ></div>
                      {t("import.reading")}
                    </div>
                  ) : (
                    t("import.read")
                  )}
                </button>
              </div>
            </div>

            {listedCalculationFiles.length > 0 && (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-medium text-gray-700">
                    {t("import.excelFilesFound", {
                      count: listedCalculationFiles.length,
                    })}
                  </p>
                  <button
                    onClick={clearCalculationFiles}
                    className="text-sm text-gray-500 hover:text-gray-700"
                  >
                    {t("import.clearAll")}
                  </button>
                </div>

                <div className="border border-gray-200 rounded-md max-h-64 overflow-y-auto divide-y divide-gray-100">
                  {listedCalculationFiles.map((filePath) => (
                    <div
                      key={filePath}
                      className="flex items-center justify-between gap-2 px-3 py-2 text-sm hover:bg-gray-50"
                    >
                      <div
                        className="flex items-center min-w-0 flex-1"
                        title={filePath}
                      >
                        <FileSpreadsheet
                          className={`h-4 w-4 text-green-600 shrink-0 ${
                            isRTL ? "ml-2" : "mr-2"
                          }`}
                        />
                        <span className="truncate text-gray-900">
                          {getFileDisplayName(filePath)}
                        </span>
                        <span className="hidden sm:inline truncate text-gray-400 text-xs ml-2">
                          {filePath}
                        </span>
                      </div>
                      <button
                        onClick={() => handleRemoveListedFile(filePath)}
                        className="shrink-0 p-1 text-gray-400 hover:text-red-600 rounded"
                        title={t("import.removeFromList")}
                      >
                        <X className="h-4 w-4" />
                      </button>
                    </div>
                  ))}
                </div>

                <button
                  onClick={handleCalculationImport}
                  disabled={calculationImportMutation.isLoading}
                  className="btn btn-success btn-md w-full"
                >
                  {calculationImportMutation.isLoading ? (
                    <div className="flex items-center justify-center">
                      <div
                        className={`animate-spin rounded-full h-4 w-4 border-b-2 border-white ${
                          isRTL ? "ml-2" : "mr-2"
                        }`}
                      ></div>
                      {t("import.importing")}
                    </div>
                  ) : (
                    <div className="flex items-center justify-center">
                      <Upload
                        className={`h-4 w-4 ${isRTL ? "ml-2" : "mr-2"}`}
                      />
                      {t("import.importCalculationSheets")}
                    </div>
                  )}
                </button>
              </div>
            )}
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
