import React, { useState } from "react";
import { useMutation, useQueryClient } from "react-query";
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
      toast.success("BOQ file imported successfully!");
      // Refresh the dashboard data
      queryClient.invalidateQueries("boq-items");
      queryClient.invalidateQueries("summary");
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || "Failed to import BOQ file");
    },
  });

  const calculationImportMutation = useMutation(
    importApi.importCalculationSheets,
    {
      onSuccess: (data) => {
        setCalculationImportResult(data);
        toast.success("Calculation sheets imported successfully!");
        // Refresh the calculation sheets data
        queryClient.invalidateQueries("calculation-sheets");
      },
      onError: (error: any) => {
        toast.error(
          error.response?.data?.detail || "Failed to import calculation sheets"
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
      toast.error("Please select a valid Excel file (.xlsx or .xls)");
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
      toast.error("No valid Excel files found in the selected folder");
      return;
    }

    setSelectedFolder(files);
    setCalculationImportResult(null);
    toast.success(`Found ${excelFiles.length} Excel files`);
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
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">File Import</h1>
        <p className="mt-2 text-gray-600">
          Import BOQ files and calculation sheets
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Left Side - BOQ File Import */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="space-y-4">
            <div>
              <h2 className="text-lg font-semibold text-gray-900 mb-2">
                Import BOQ File
              </h2>
              <p className="text-sm text-gray-600">
                Upload your BOQ.xlsx file. Items with existing section numbers
                will be skipped (not overwritten).
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
                          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                          Importing...
                        </div>
                      ) : (
                        <div className="flex items-center">
                          <Upload className="h-4 w-4 mr-2" />
                          Import File
                        </div>
                      )}
                    </button>
                    <button
                      onClick={clearFile}
                      className="btn btn-outline btn-md"
                    >
                      <X className="h-4 w-4 mr-2" />
                      Clear
                    </button>
                  </div>
                </div>
              ) : (
                <div className="space-y-4">
                  <Upload className="h-12 w-12 text-gray-400 mx-auto" />
                  <div>
                    <p className="text-lg font-medium text-gray-900">
                      Drop your BOQ file here
                    </p>
                    <p className="text-sm text-gray-500">
                      or click to browse files
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
                    <Upload className="h-4 w-4 mr-2" />
                    Choose File
                  </label>
                </div>
              )}
            </div>
          </div>

          {/* BOQ Import Results */}
          {importResult && (
            <div className="mt-6 space-y-4">
              <h3 className="text-md font-semibold text-gray-900">
                Import Results
              </h3>

              <div
                className={`flex items-center p-4 rounded-lg ${
                  importResult.success
                    ? "bg-green-50 border border-green-200"
                    : "bg-red-50 border border-red-200"
                }`}
              >
                {importResult.success ? (
                  <CheckCircle className="h-5 w-5 text-green-500 mr-3" />
                ) : (
                  <AlertCircle className="h-5 w-5 text-red-500 mr-3" />
                )}
                <div>
                  <p
                    className={`font-medium ${
                      importResult.success ? "text-green-800" : "text-red-800"
                    }`}
                  >
                    {importResult.success
                      ? "Import Successful"
                      : "Import Failed"}
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
                    Files Processed
                  </p>
                  <p className="text-xl font-bold text-gray-900">
                    {importResult.files_processed}
                  </p>
                </div>
                <div className="bg-gray-50 p-3 rounded-lg">
                  <p className="text-sm font-medium text-gray-600">
                    Items Imported
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
                    Import Details:
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
                Import Calculation Sheets
              </h2>
              <p className="text-sm text-gray-600">
                Upload a folder containing calculation sheet Excel files. The
                system will extract calculation data from each sheet.
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
                      Folder Selected
                    </p>
                    <p className="text-sm text-gray-500">
                      {getExcelFilesCount()} Excel files found
                    </p>
                    <div className="mt-2 text-xs text-gray-400 max-h-20 overflow-y-auto">
                      {Array.from(selectedFolder)
                        .slice(0, 5)
                        .map((file, index) => (
                          <div
                            key={index}
                            className="flex items-center justify-center"
                          >
                            <FileSpreadsheet className="h-3 w-3 mr-1" />
                            {file.name}
                          </div>
                        ))}
                      {selectedFolder.length > 5 && (
                        <div className="text-gray-400">
                          ... and {selectedFolder.length - 5} more
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
                          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                          Importing...
                        </div>
                      ) : (
                        <div className="flex items-center">
                          <Upload className="h-4 w-4 mr-2" />
                          Import Sheets
                        </div>
                      )}
                    </button>
                    <button
                      onClick={clearFolder}
                      className="btn btn-outline btn-md"
                    >
                      <X className="h-4 w-4 mr-2" />
                      Clear
                    </button>
                  </div>
                </div>
              ) : (
                <div className="space-y-4">
                  <FolderOpen className="h-12 w-12 text-gray-400 mx-auto" />
                  <div>
                    <p className="text-lg font-medium text-gray-900">
                      Drop calculation sheets folder here
                    </p>
                    <p className="text-sm text-gray-500">
                      or click to browse folder
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
                    <FolderOpen className="h-4 w-4 mr-2" />
                    Choose Folder
                  </label>
                </div>
              )}
            </div>
          </div>

          {/* Calculation Sheets Import Results */}
          {calculationImportResult && (
            <div className="mt-6 space-y-4">
              <h3 className="text-md font-semibold text-gray-900">
                Import Results
              </h3>

              <div
                className={`flex items-center p-4 rounded-lg ${
                  calculationImportResult.success
                    ? "bg-green-50 border border-green-200"
                    : "bg-red-50 border border-red-200"
                }`}
              >
                {calculationImportResult.success ? (
                  <CheckCircle className="h-5 w-5 text-green-500 mr-3" />
                ) : (
                  <AlertCircle className="h-5 w-5 text-red-500 mr-3" />
                )}
                <div>
                  <p
                    className={`font-medium ${
                      calculationImportResult.success
                        ? "text-green-800"
                        : "text-red-800"
                    }`}
                  >
                    {calculationImportResult.success
                      ? "Import Successful"
                      : "Import Failed"}
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
                    Files Processed
                  </p>
                  <p className="text-xl font-bold text-gray-900">
                    {calculationImportResult.files_processed || 0}
                  </p>
                </div>
                <div className="bg-gray-50 p-3 rounded-lg">
                  <p className="text-sm font-medium text-gray-600">
                    Sheets Imported
                  </p>
                  <p className="text-xl font-bold text-gray-900">
                    {calculationImportResult.sheets_imported || 0}
                  </p>
                </div>
                <div className="bg-gray-50 p-3 rounded-lg">
                  <p className="text-sm font-medium text-gray-600">
                    Entries Imported
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
                      Import Details:
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

      {/* Instructions */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-blue-900 mb-4">
          Import Instructions
        </h3>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div>
            <h4 className="text-md font-semibold text-blue-800 mb-2">
              BOQ File Import:
            </h4>
            <ul className="text-sm text-blue-800 space-y-2">
              <li className="flex items-start">
                <span className="text-blue-500 mr-2">•</span>
                Upload your BOQ.xlsx file containing the Bill of Quantities data
              </li>
              <li className="flex items-start">
                <span className="text-blue-500 mr-2">•</span>
                The system uses "Section Number" as the unique identifier for
                each item
              </li>
              <li className="flex items-start">
                <span className="text-blue-500 mr-2">•</span>
                Items with existing section numbers will be skipped (not
                overwritten)
              </li>
              <li className="flex items-start">
                <span className="text-blue-500 mr-2">•</span>
                Supported file formats: .xlsx, .xls
              </li>
            </ul>
          </div>

          <div>
            <h4 className="text-md font-semibold text-blue-800 mb-2">
              Calculation Sheets Import:
            </h4>
            <ul className="text-sm text-blue-800 space-y-2">
              <li className="flex items-start">
                <span className="text-blue-500 mr-2">•</span>
                Upload a folder containing multiple calculation sheet Excel
                files
              </li>
              <li className="flex items-start">
                <span className="text-blue-500 mr-2">•</span>
                Each sheet must have data in specific cells (C1, C2, C3, J5-L5,
                J6-L6, J24-L24)
              </li>
              <li className="flex items-start">
                <span className="text-blue-500 mr-2">•</span>
                The system extracts: Sheet No, Drawing No, Description, Section
                Numbers, Quantities
              </li>
              <li className="flex items-start">
                <span className="text-blue-500 mr-2">•</span>
                Data is automatically saved to the database for each calculation
                sheet
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

export default FileImport;
