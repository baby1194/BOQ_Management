import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import toast from "react-hot-toast";
import { useLanguage } from "../contexts/LanguageContext";
import {
  boqApi,
  searchApi,
  concentrationApi,
  calculationSheetsApi,
  nonBoqApi,
  exportApi,
} from "../services/api";
import {
  BarChart3,
  FileText,
  Calculator,
  Upload,
  Download,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  CheckCircle,
  Clock,
  DollarSign,
  Package,
  Users,
  Building,
  PieChart,
  Activity,
  ArrowUpRight,
  ArrowDownRight,
  Eye,
  Plus,
  Settings,
  FileSpreadsheet,
  ChevronDown,
  ChevronRight,
  FileCheck,
  Files,
} from "lucide-react";
import { formatCurrency } from "../utils/format";
import { useProject } from "../contexts/ProjectContext";
import { getActiveProjectId, getProjectItem, setProjectItem } from "../utils/localStorage";
import { setActiveProjectIdForApi } from "../services/api";
import {
  BOQItem,
  ConcentrationSheet,
  CalculationSheet,
  SummaryResponse,
  NonBoqItem,
  ApprovedSignedQtyImportResponse,
} from "../types";
import ReadApprovedSignedQtyModal from "../components/ReadApprovedSignedQtyModal";

const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const { isRTL } = useLanguage();
  const [selectedPeriod, setSelectedPeriod] = useState("all");
  const { activeProjectId, projects } = useProject();

  const projectId =
    getActiveProjectId() ?? activeProjectId ?? projects[0]?.id ?? null;

  const [boqItems, setBoqItems] = useState<BOQItem[] | null>(null);
  const [summary, setSummary] = useState<SummaryResponse | null>(null);
  const [concentrationSheets, setConcentrationSheets] = useState<
    ConcentrationSheet[] | null
  >(null);
  const [calculationSheets, setCalculationSheets] = useState<
    CalculationSheet[] | null
  >(null);
  const [nonBoqItems, setNonBoqItems] = useState<NonBoqItem[]>([]);
  const [removingNonBoqId, setRemovingNonBoqId] = useState<number | null>(null);
  const [exportingNonBoq, setExportingNonBoq] = useState<"pdf" | "excel" | null>(
    null,
  );
  const [nonBoqExpanded, setNonBoqExpanded] = useState(() => {
    const saved = getProjectItem("dashboard-non-boq-expanded");
    return saved === null ? true : saved === "true";
  });
  const [isLoading, setIsLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [showApprovedSignedQtyModal, setShowApprovedSignedQtyModal] =
    useState(false);
  const [producingFinalSubmission, setProducingFinalSubmission] =
    useState(false);

  const handleProduceFinalSubmissionPdf = async () => {
    if (producingFinalSubmission) return;
    setProducingFinalSubmission(true);
    const toastId = toast.loading(t("dashboard.producingFinalSubmissionPdf"));
    try {
      const result = await exportApi.produceFinalSubmissionPDF();
      if (result.success) {
        toast.success(
          result.message ||
            t("dashboard.finalSubmissionPdfSuccess", {
              count: result.sheets_exported,
            }),
          { id: toastId },
        );
      } else {
        toast.error(
          result.message || t("dashboard.finalSubmissionPdfFailed"),
          { id: toastId },
        );
      }
    } catch (error: any) {
      console.error("Final submission PDF failed:", error);
      toast.error(
        error?.response?.data?.detail ||
          error?.message ||
          t("dashboard.finalSubmissionPdfFailed"),
        { id: toastId },
      );
    } finally {
      setProducingFinalSubmission(false);
    }
  };

  useEffect(() => {
    setProjectItem(
      "dashboard-non-boq-expanded",
      nonBoqExpanded ? "true" : "false",
    );
  }, [nonBoqExpanded]);

  useEffect(() => {
    if (!projectId) {
      setIsLoading(false);
      return;
    }

    setActiveProjectIdForApi(projectId);

    let cancelled = false;
    setIsLoading(true);
    setLoadError(null);

    Promise.all([
      boqApi.getAll(),
      searchApi.getSummary(),
      concentrationApi.getAll(),
      calculationSheetsApi.getAll(),
      nonBoqApi.getAll(),
    ])
      .then(([boq, summaryData, concentration, calculation, nonBoq]) => {
        if (cancelled) return;
        setBoqItems(boq);
        setSummary(summaryData);
        setConcentrationSheets(concentration);
        setCalculationSheets(calculation);
        setNonBoqItems(nonBoq);
      })
      .catch((error) => {
        if (cancelled) return;
        console.error("Dashboard load failed:", error);
        setLoadError(
          error?.response?.data?.detail ||
            error?.message ||
            "Failed to load dashboard"
        );
      })
      .finally(() => {
        if (!cancelled) {
          setIsLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [projectId]);

  // Calculate comprehensive statistics
  const calculateStats = () => {
    if (!boqItems || !concentrationSheets || !calculationSheets) return {};

    const totalBOQItems = boqItems.length;
    const totalConcentrationSheets = concentrationSheets.length;
    const totalCalculationSheets = calculationSheets.length;

    // Financial totals
    const totalContractValue = boqItems.reduce(
      (sum, item) => sum + (item.total_contract_sum || 0),
      0
    );
    const totalEstimateValue = boqItems.reduce(
      (sum, item) => sum + (item.total_estimate || 0),
      0
    );
    const totalSubmittedValue = boqItems.reduce(
      (sum, item) => sum + (item.total_submitted || 0),
      0
    );
    const totalInternalValue = boqItems.reduce(
      (sum, item) => sum + (item.internal_total || 0),
      0
    );
    const totalApprovedValue = boqItems.reduce(
      (sum, item) => sum + (item.approved_signed_total || 0),
      0
    );

    // Variances
    const estimateVariance = totalEstimateValue - totalContractValue;
    const submittedVariance = totalSubmittedValue - totalContractValue;
    const approvedVariance = totalApprovedValue - totalContractValue;

    // Progress indicators
    const estimateProgress =
      totalContractValue > 0
        ? (totalEstimateValue / totalContractValue) * 100
        : 0;
    const submittedProgress =
      totalContractValue > 0
        ? (totalSubmittedValue / totalContractValue) * 100
        : 0;
    const approvedProgress =
      totalContractValue > 0
        ? (totalApprovedValue / totalContractValue) * 100
        : 0;

    // Status counts
    const itemsWithEntries = boqItems.filter((item) =>
      concentrationSheets.some((sheet) => sheet.boq_item_id === item.id)
    ).length;

    const itemsWithoutEntries = totalBOQItems - itemsWithEntries;

    return {
      totalBOQItems,
      totalConcentrationSheets,
      totalCalculationSheets,
      totalContractValue,
      totalEstimateValue,
      totalSubmittedValue,
      totalInternalValue,
      totalApprovedValue,
      estimateVariance,
      submittedVariance,
      approvedVariance,
      estimateProgress,
      submittedProgress,
      approvedProgress,
      itemsWithEntries,
      itemsWithoutEntries,
    };
  };

  const stats = calculateStats();

  const handleRemoveNonBoqItem = async (item: NonBoqItem) => {
    setRemovingNonBoqId(item.id);
    try {
      await nonBoqApi.remove(item.id);
      setNonBoqItems((prev) => prev.filter((entry) => entry.id !== item.id));
    } catch (error) {
      console.error("Failed to remove non-BOQ item:", error);
    } finally {
      setRemovingNonBoqId(null);
    }
  };

  const handleAddNonBoqToBoq = (sectionNumber: string) => {
    navigate(
      `/boq?addSection=${encodeURIComponent(sectionNumber)}`,
    );
  };

  const handleExportNonBoqItems = async (format: "pdf" | "excel") => {
    if (nonBoqItems.length === 0) {
      return;
    }

    setExportingNonBoq(format);
    try {
      const language = isRTL ? "he" : "en";
      const response =
        format === "pdf"
          ? await exportApi.exportNonBoqItemsPDF(language)
          : await exportApi.exportNonBoqItemsExcel(language);

      if (response.success && response.pdf_path) {
        await exportApi.downloadExportFile(response.pdf_path);
      }
    } catch (error) {
      console.error(`Failed to export non-BOQ items as ${format}:`, error);
    } finally {
      setExportingNonBoq(null);
    }
  };

  const reloadDashboardData = async () => {
    if (!projectId) {
      return;
    }
    try {
      const [boq, summaryData, concentration, calculation, nonBoq] =
        await Promise.all([
          boqApi.getAll(),
          searchApi.getSummary(),
          concentrationApi.getAll(),
          calculationSheetsApi.getAll(),
          nonBoqApi.getAll(),
        ]);
      setBoqItems(boq);
      setSummary(summaryData);
      setConcentrationSheets(concentration);
      setCalculationSheets(calculation);
      setNonBoqItems(nonBoq);
    } catch (error) {
      console.error("Dashboard reload failed:", error);
    }
  };

  const handleApprovedSignedQtySuccess = async (
    _result: ApprovedSignedQtyImportResponse,
  ) => {
    await reloadDashboardData();
  };

  const formatNonBoqCalcSheets = (item: NonBoqItem) => {
    const sheetNos = item.calculation_sheet_nos?.filter(Boolean) ?? [];
    if (sheetNos.length === 0) {
      return null;
    }
    return sheetNos.join(", ");
  };

  // Main statistics cards
  const mainStats = [
    {
      name: t("dashboard.totalBOQItems"),
      value: stats.totalBOQItems || 0,
      icon: FileText,
      color: "bg-blue-500",
      change: null,
      description: t("dashboard.totalBillQuantitiesItems"),
    },
    {
      name: t("dashboard.concentrationSheets"),
      value: stats.totalConcentrationSheets || 0,
      icon: Calculator,
      color: "bg-green-500",
      change: stats.itemsWithEntries || 0,
      description: `${t("dashboard.active")}: ${
        stats.itemsWithEntries || 0
      }, ${t("dashboard.pending")}: ${stats.itemsWithoutEntries || 0}`,
    },
    {
      name: t("dashboard.calculationSheets"),
      value: stats.totalCalculationSheets || 0,
      icon: TrendingUp,
      color: "bg-purple-500",
      change: null,
      description: t("dashboard.importedCalculationSheets"),
    },
    {
      name: t("dashboard.contractValue"),
      value: formatCurrency(stats.totalContractValue || 0),
      icon: DollarSign,
      color: "bg-yellow-500",
      change: null,
      description: t("dashboard.totalContractValue"),
    },
  ];

  // Financial metrics
  const financialMetrics = [
    {
      name: t("dashboard.totalEstimate"),
      value: formatCurrency(stats.totalEstimateValue || 0),
      change: formatCurrency(Math.abs(stats.estimateVariance || 0)),
      changeType: (stats.estimateVariance || 0) >= 0 ? "positive" : "negative",
      progress: stats.estimateProgress || 0,
      icon: TrendingUp,
    },
    {
      name: t("dashboard.totalSubmitted"),
      value: formatCurrency(stats.totalSubmittedValue || 0),
      change: formatCurrency(Math.abs(stats.submittedVariance || 0)),
      changeType: (stats.submittedVariance || 0) >= 0 ? "positive" : "negative",
      progress: stats.submittedProgress || 0,
      icon: Upload,
    },
    {
      name: t("dashboard.totalApproved"),
      value: formatCurrency(stats.totalApprovedValue || 0),
      change: formatCurrency(Math.abs(stats.approvedVariance || 0)),
      changeType: (stats.approvedVariance || 0) >= 0 ? "positive" : "negative",
      progress: stats.approvedProgress || 0,
      icon: CheckCircle,
    },
  ];

  // Recent activity simulation (in a real app, this would come from an API)
  const recentActivity = [
    {
      id: 1,
      type: "import",
      message: t("dashboard.importedSuccessfully"),
      timestamp: `2 ${t("dashboard.hoursAgo")}`,
      icon: Upload,
      color: "text-green-600",
    },
    {
      id: 2,
      type: "calculation",
      message: t("dashboard.calculationSheetProcessed"),
      timestamp: `4 ${t("dashboard.hoursAgo")}`,
      icon: Calculator,
      color: "text-blue-600",
    },
    {
      id: 3,
      type: "concentration",
      message: t("dashboard.concentrationEntriesPopulated"),
      timestamp: `6 ${t("dashboard.hoursAgo")}`,
      icon: TrendingUp,
      color: "text-purple-600",
    },
    {
      id: 4,
      type: "export",
      message: t("dashboard.excelReportGenerated"),
      timestamp: `1 ${t("dashboard.dayAgo")}`,
      icon: Download,
      color: "text-orange-600",
    },
  ];

  // Quick actions
  const quickActions = [
    {
      name: t("dashboard.importBOQFile"),
      description: t("dashboard.uploadAndProcessBOQExcelFile"),
      icon: Upload,
      color: "bg-blue-600 hover:bg-blue-700",
      action: () => navigate("/import"),
    },
    {
      name: t("dashboard.readApprovedSignedQty"),
      description: t("dashboard.readApprovedSignedQtyActionDescription"),
      icon: FileCheck,
      color: "bg-teal-600 hover:bg-teal-700",
      action: () => setShowApprovedSignedQtyModal(true),
    },
    {
      name: t("dashboard.produceFinalSubmissionPdf"),
      description: t("dashboard.produceFinalSubmissionPdfDescription"),
      icon: Files,
      color: producingFinalSubmission
        ? "bg-indigo-400 cursor-wait"
        : "bg-indigo-600 hover:bg-indigo-700",
      action: handleProduceFinalSubmissionPdf,
      disabled: producingFinalSubmission,
    },
    {
      name: t("dashboard.viewBOQItems"),
      description: t("dashboard.browseAndManageBOQItems"),
      icon: FileText,
      color: "bg-green-600 hover:bg-green-700",
      action: () => navigate("/boq"),
    },
    {
      name: t("dashboard.concentrationSheets"),
      description: t("dashboard.manageConcentrationEntries"),
      icon: Calculator,
      color: "bg-purple-600 hover:bg-purple-700",
      action: () => navigate("/concentration"),
    },
    {
      name: t("dashboard.calculationSheets"),
      description: t("dashboard.viewImportedCalculationData"),
      icon: TrendingUp,
      color: "bg-orange-600 hover:bg-orange-700",
      action: () => navigate("/calculation-sheets"),
    },
  ];

  if (loadError) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center text-red-600">
          <p className="text-lg font-medium">{loadError}</p>
          <button
            onClick={() => window.location.reload()}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <div className="text-lg text-gray-600">
            {t("dashboard.loadingDashboard")}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">
            {t("dashboard.title")}
          </h1>
          <p className="mt-2 text-gray-600">
            {t("dashboard.comprehensiveOverview")}
          </p>
        </div>
        <div className="flex space-x-3">
          <select
            value={selectedPeriod}
            onChange={(e) => setSelectedPeriod(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">{t("dashboard.allTime")}</option>
            <option value="month">{t("dashboard.thisMonth")}</option>
            <option value="week">{t("dashboard.thisWeek")}</option>
            <option value="today">{t("dashboard.today")}</option>
          </select>
          <button
            onClick={() => window.location.reload()}
            className="p-2 text-gray-400 hover:text-gray-600 transition-colors"
            title={t("dashboard.refreshData")}
          >
            <Activity className="h-5 w-5" />
          </button>
          <button
            onClick={() => navigate("/settings")}
            className="p-2 text-gray-400 hover:text-gray-600 transition-colors"
            title={t("dashboard.settings")}
          >
            <Settings className="h-5 w-5" />
          </button>
        </div>
      </div>

      {/* Main Statistics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {mainStats.map((stat) => {
          const Icon = stat.icon;
          return (
            <div key={stat.name} className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center justify-between">
                <div className="flex items-center">
                  <div className={`p-3 rounded-lg ${stat.color}`}>
                    <Icon className="h-6 w-6 text-white" />
                  </div>
                  <div className={`${isRTL ? "mr-4" : "ml-4"}`}>
                    <p className="text-sm font-medium text-gray-600">
                      {stat.name}
                    </p>
                    <p className="text-2xl font-semibold text-gray-900">
                      {stat.value}
                    </p>
                  </div>
                </div>
                {stat.change !== null && (
                  <div className={isRTL ? "text-left" : "text-right"}>
                    <p
                      className={`text-sm text-gray-500 ${
                        isRTL ? "text-left" : "text-right"
                      }`}
                    >
                      {t("dashboard.active")}
                    </p>
                    <p
                      className={`text-lg font-semibold text-green-600 ${
                        isRTL ? "text-left" : "text-right"
                      }`}
                    >
                      {stat.change}
                    </p>
                  </div>
                )}
              </div>
              <p className="text-xs text-gray-500 mt-3">{stat.description}</p>
            </div>
          );
        })}
      </div>

      {/* Financial Metrics */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {financialMetrics.map((metric) => {
          const Icon = metric.icon;
          return (
            <div key={metric.name} className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center">
                  <Icon
                    className={`h-5 w-5 text-gray-400 ${
                      isRTL ? "ml-2" : "mr-2"
                    }`}
                  />
                  <h3 className="text-lg font-medium text-gray-900">
                    {metric.name}
                  </h3>
                </div>
                <div
                  className={`flex items-center text-sm ${
                    metric.changeType === "positive"
                      ? "text-green-600"
                      : "text-red-600"
                  }`}
                >
                  {metric.changeType === "positive" ? (
                    <ArrowUpRight className="h-4 w-4 mr-1" />
                  ) : (
                    <ArrowDownRight className="h-4 w-4 mr-1" />
                  )}
                  {metric.change}
                </div>
              </div>
              <p className="text-3xl font-bold text-gray-900 mb-4">
                {metric.value}
              </p>

              {/* Progress bar */}
              <div className="mb-2">
                <div
                  className={`flex justify-between text-sm text-gray-600 mb-1 ${
                    isRTL ? "flex-row-reverse" : ""
                  }`}
                >
                  <span>{t("dashboard.progress")}</span>
                  <span className={isRTL ? "text-left" : "text-right"}>
                    {metric.progress.toFixed(1)}%
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                    style={{ width: `${Math.min(metric.progress, 100)}%` }}
                  ></div>
                </div>
              </div>

              <p className="text-xs text-gray-500">
                {metric.changeType === "positive"
                  ? t("dashboard.aboveContractValue")
                  : t("dashboard.belowContractValue")}
              </p>
            </div>
          );
        })}
      </div>

      {/* Non-BOQ Items from Calculation Sheets */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <div
            className={`flex items-start justify-between gap-4 ${
              isRTL ? "flex-row-reverse" : ""
            }`}
          >
            <button
              type="button"
              onClick={() => setNonBoqExpanded((prev) => !prev)}
              className={`flex-1 text-left ${isRTL ? "text-right" : ""}`}
              aria-expanded={nonBoqExpanded}
              title={
                nonBoqExpanded
                  ? t("dashboard.collapseNonBoqItems")
                  : t("dashboard.expandNonBoqItems")
              }
            >
              <h2
                className={`text-lg font-semibold text-gray-900 flex items-center ${
                  isRTL ? "flex-row-reverse" : ""
                }`}
              >
                {nonBoqExpanded ? (
                  <ChevronDown
                    className={`h-5 w-5 text-gray-500 ${isRTL ? "ml-2" : "mr-2"}`}
                  />
                ) : (
                  <ChevronRight
                    className={`h-5 w-5 text-gray-500 ${
                      isRTL ? "ml-2 rotate-180" : "mr-2"
                    }`}
                  />
                )}
                <AlertTriangle
                  className={`h-5 w-5 text-amber-600 ${isRTL ? "ml-2" : "mr-2"}`}
                />
                <span>{t("dashboard.nonBoqItems")}</span>
                {nonBoqItems.length > 0 && (
                  <span
                    className={`inline-flex items-center justify-center min-w-[1.5rem] h-6 px-2 text-xs font-medium rounded-full bg-amber-100 text-amber-800 ${
                      isRTL ? "mr-2" : "ml-2"
                    }`}
                  >
                    {nonBoqItems.length}
                  </span>
                )}
              </h2>
              {nonBoqExpanded && (
                <p className="text-sm text-gray-600 mt-1">
                  {t("dashboard.nonBoqItemsDescription")}
                </p>
              )}
            </button>
            {nonBoqItems.length > 0 && (
              <div
                className={`flex items-center gap-2 shrink-0 ${
                  isRTL ? "flex-row-reverse" : ""
                }`}
              >
                <button
                  onClick={() => handleExportNonBoqItems("pdf")}
                  disabled={exportingNonBoq !== null}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm bg-white text-gray-700 border border-gray-300 rounded-md hover:bg-gray-50 transition-colors disabled:opacity-50"
                  title={t("dashboard.exportNonBoqPdf")}
                >
                  <Download className="h-4 w-4" />
                  <span>
                    {exportingNonBoq === "pdf"
                      ? t("dashboard.exportingNonBoqItems")
                      : t("dashboard.exportNonBoqPdf")}
                  </span>
                </button>
                <button
                  onClick={() => handleExportNonBoqItems("excel")}
                  disabled={exportingNonBoq !== null}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm bg-white text-gray-700 border border-gray-300 rounded-md hover:bg-gray-50 transition-colors disabled:opacity-50"
                  title={t("dashboard.exportNonBoqExcel")}
                >
                  <FileSpreadsheet className="h-4 w-4" />
                  <span>
                    {exportingNonBoq === "excel"
                      ? t("dashboard.exportingNonBoqItems")
                      : t("dashboard.exportNonBoqExcel")}
                  </span>
                </button>
              </div>
            )}
          </div>
        </div>
        {nonBoqExpanded && (
          <div className="p-6">
            {nonBoqItems.length > 0 ? (
              <div className="space-y-3">
                {nonBoqItems.map((item) => (
                  <div
                    key={item.id}
                    className={`flex items-center justify-between gap-4 p-3 bg-amber-50 rounded-lg border border-amber-200 ${
                      isRTL ? "flex-row-reverse" : ""
                    }`}
                  >
                    <div>
                      <p className="font-medium text-gray-900">
                        {t("boq.sectionNumber")}: {item.section_number}
                        {formatNonBoqCalcSheets(item) && (
                          <>
                            <span className="mx-2 text-gray-400">·</span>
                            <span className="font-normal text-gray-700">
                              {t("concentration.calcSheetNo")}:{" "}
                              {formatNonBoqCalcSheets(item)}
                            </span>
                          </>
                        )}
                      </p>
                    </div>
                    <div
                      className={`flex items-center gap-2 shrink-0 ${
                        isRTL ? "flex-row-reverse" : ""
                      }`}
                    >
                      <button
                        onClick={() =>
                          handleAddNonBoqToBoq(item.section_number)
                        }
                        className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
                      >
                        {t("dashboard.addToBoqList")}
                      </button>
                      <button
                        onClick={() => handleRemoveNonBoqItem(item)}
                        disabled={removingNonBoqId === item.id}
                        className="px-3 py-1.5 text-sm bg-white text-gray-700 border border-gray-300 rounded-md hover:bg-gray-50 transition-colors disabled:opacity-50"
                      >
                        {removingNonBoqId === item.id
                          ? t("dashboard.removingNonBoqItem")
                          : t("dashboard.removeFromList")}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center text-gray-500 py-8">
                <CheckCircle className="h-12 w-12 mx-auto mb-4 text-green-300" />
                <p>{t("dashboard.noNonBoqItems")}</p>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Summary Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Sub-chapters Summary */}
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2
              className={`text-lg font-semibold text-gray-900 flex items-center ${
                isRTL ? "flex-row-reverse" : ""
              }`}
            >
              <PieChart
                className={`h-5 w-5 text-blue-600 ${isRTL ? "ml-2" : "mr-2"}`}
              />
              <span>{t("dashboard.subChaptersSummary")}</span>
            </h2>
          </div>
          <div className="p-6">
            {summary?.summaries ? (
              <div className="space-y-4">
                {summary.summaries.slice(0, 5).map((item, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                  >
                    <div>
                      <p className="font-medium text-gray-900">
                        {item.sub_chapter}
                      </p>
                      <p className="text-sm text-gray-600">
                        {item.item_count} {t("dashboard.items")}
                      </p>
                    </div>
                    <div className={isRTL ? "text-left" : "text-right"}>
                      <p
                        className={`font-semibold text-gray-900 ${
                          isRTL ? "text-left" : "text-right"
                        }`}
                      >
                        ${item.total_estimate.toLocaleString()}
                      </p>
                      <p
                        className={`text-sm text-gray-600 ${
                          isRTL ? "text-left" : "text-right"
                        }`}
                      >
                        {t("dashboard.estimate")}
                      </p>
                    </div>
                  </div>
                ))}
                {summary.summaries.length > 5 && (
                  <div className="text-center pt-2">
                    <button className="text-blue-600 hover:text-blue-800 text-sm font-medium">
                      {t("dashboard.viewAllSubChapters", {
                        count: summary.summaries.length,
                      })}
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center text-gray-500 py-8">
                <PieChart className="h-12 w-12 mx-auto mb-4 text-gray-300" />
                <p>{t("dashboard.noSubChapterDataAvailable")}</p>
              </div>
            )}
          </div>
        </div>

        {/* System Status */}
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2
              className={`text-lg font-semibold text-gray-900 flex items-center ${
                isRTL ? "flex-row-reverse" : ""
              }`}
            >
              <Activity
                className={`h-5 w-5 text-green-600 ${isRTL ? "ml-2" : "mr-2"}`}
              />
              <span>{t("dashboard.systemStatus")}</span>
            </h2>
          </div>
          <div className="p-6">
            <div className="space-y-4">
              <div className="flex items-center justify-between p-3 bg-green-50 rounded-lg border border-green-200">
                <div className="flex items-center">
                  <CheckCircle className="h-5 w-5 text-green-600 mr-3" />
                  <div>
                    <p className="font-medium text-green-900">
                      {t("dashboard.systemOperational")}
                    </p>
                    <p className="text-sm text-green-700">
                      {t("dashboard.allServicesRunningNormally")}
                    </p>
                  </div>
                </div>
                <span className="text-green-600 text-sm font-medium">
                  ✓ {t("dashboard.active")}
                </span>
              </div>

              <div className="flex items-center justify-between p-3 bg-blue-50 rounded-lg border border-blue-200">
                <div className="flex items-center">
                  <Package className="h-5 w-5 text-blue-600 mr-3" />
                  <div>
                    <p className="font-medium text-blue-900">
                      {t("dashboard.dataIntegrity")}
                    </p>
                    <p className="text-sm text-blue-700">
                      {t("dashboard.boqItemsValidated", {
                        count: stats.totalBOQItems || 0,
                      })}
                    </p>
                  </div>
                </div>
                <span
                  className={`text-blue-600 text-sm font-medium ${
                    isRTL ? "text-left" : "text-right"
                  }`}
                >
                  ✓ {t("dashboard.valid")}
                </span>
              </div>

              <div className="flex items-center justify-between p-3 bg-yellow-50 rounded-lg border border-yellow-200">
                <div className="flex items-center">
                  <AlertTriangle className="h-5 w-5 text-yellow-600 mr-3" />
                  <div>
                    <p className="font-medium text-yellow-900">
                      {t("dashboard.pendingActions")}
                    </p>
                    <p className="text-sm text-yellow-700">
                      {t("dashboard.itemsNeedConcentrationSheets", {
                        count: stats.itemsWithoutEntries || 0,
                      })}
                    </p>
                  </div>
                </div>
                <span
                  className={`text-yellow-600 text-sm font-medium ${
                    isRTL ? "text-left" : "text-right"
                  }`}
                >
                  ⚠ {t("dashboard.pending")}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2
            className={`text-lg font-semibold text-gray-900 flex items-center ${
              isRTL ? "flex-row-reverse" : ""
            }`}
          >
            <Clock
              className={`h-5 w-5 text-gray-600 ${isRTL ? "ml-2" : "mr-2"}`}
            />
            <span>{t("dashboard.recentActivity")}</span>
          </h2>
        </div>
        <div className="p-6">
          {recentActivity.length > 0 ? (
            <div className="space-y-4">
              {recentActivity.map((activity) => {
                const Icon = activity.icon;
                return (
                  <div
                    key={activity.id}
                    className="flex items-center p-3 hover:bg-gray-50 rounded-lg transition-colors"
                  >
                    <div
                      className={`p-2 rounded-lg bg-gray-100 ${activity.color}`}
                    >
                      <Icon className="h-4 w-4" />
                    </div>
                    <div className={`${isRTL ? "mr-4" : "ml-4"} flex-1`}>
                      <p className="text-sm font-medium text-gray-900">
                        {activity.message}
                      </p>
                      <p className="text-xs text-gray-500">
                        {activity.timestamp}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="text-center text-gray-500 py-8">
              <Clock className="h-12 w-12 mx-auto mb-4 text-gray-300" />
              <p>{t("dashboard.noRecentActivityDisplay")}</p>
              <p className="text-sm">
                {t("dashboard.importBOQFileToGetStarted")}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Quick Actions */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">
            {t("dashboard.quickActions")}
          </h2>
        </div>
        <div className="p-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
            {quickActions.map((action) => {
              const Icon = action.icon;
              return (
                <button
                  key={action.name}
                  onClick={action.action}
                  disabled={Boolean(action.disabled)}
                  className={`${action.color} text-white px-4 py-3 rounded-lg transition-all duration-200 transform hover:scale-105 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-70 disabled:transform-none disabled:hover:scale-100`}
                >
                  <div className="flex flex-col items-center text-center">
                    <Icon className="h-6 w-6 mb-2" />
                    <span className="font-medium">{action.name}</span>
                    <span className="text-xs opacity-90 mt-1">
                      {action.description}
                    </span>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Additional Insights */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Export Options */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3
            className={`text-lg font-semibold text-gray-900 mb-4 flex items-center ${
              isRTL ? "flex-row-reverse" : ""
            }`}
          >
            <Download
              className={`h-5 w-5 text-blue-600 ${isRTL ? "ml-2" : "mr-2"}`}
            />
            <span>{t("dashboard.exportOptions")}</span>
          </h3>
          <div className="space-y-3">
            <button
              onClick={() => navigate("/boq")}
              className="w-full text-left p-3 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors cursor-pointer"
            >
              <div className="flex items-center justify-between">
                <span className="font-medium text-gray-900">
                  {t("dashboard.boqSummaryReport")}
                </span>
                <Download className="h-4 w-4 text-gray-400" />
              </div>
              <p className="text-sm text-gray-600">
                {t("dashboard.pdfSummaryAllBOQItems")}
              </p>
            </button>
            <button
              onClick={() => navigate("/concentration")}
              className="w-full text-left p-3 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors cursor-pointer"
            >
              <div className="flex items-center justify-between">
                <span className="font-medium text-gray-900">
                  {t("dashboard.concentrationSheets")}
                </span>
                <Download className="h-4 w-4 text-gray-400" />
              </div>
              <p className="text-sm text-gray-600">
                {t("dashboard.excelExportWithAllData")}
              </p>
            </button>
            <button
              onClick={() => navigate("/calculation-sheets")}
              className="w-full text-left p-3 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors cursor-pointer"
            >
              <div className="flex items-center justify-between">
                <span className="font-medium text-gray-900">
                  {t("dashboard.calculationSheets")}
                </span>
                <Download className="h-4 w-4 text-gray-400" />
              </div>
              <p className="text-sm text-gray-600">
                {t("dashboard.viewAndExportCalculationData")}
              </p>
            </button>
          </div>
        </div>

        {/* Performance Metrics */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3
            className={`text-lg font-semibold text-gray-900 mb-4 flex items-center ${
              isRTL ? "flex-row-reverse" : ""
            }`}
          >
            <TrendingUp
              className={`h-5 w-5 text-green-600 ${isRTL ? "ml-2" : "mr-2"}`}
            />
            <span>{t("dashboard.performance")}</span>
          </h3>
          <div className="space-y-4">
            <div
              className={`flex justify-between items-center ${
                isRTL ? "flex-row-reverse" : ""
              }`}
            >
              <span className="text-gray-600">
                {t("dashboard.dataCompleteness")}
              </span>
              <span
                className={`font-semibold text-gray-900 ${
                  isRTL ? "text-left" : "text-right"
                }`}
              >
                {(stats.totalBOQItems || 0) > 0
                  ? Math.round(
                      ((stats.itemsWithEntries || 0) /
                        (stats.totalBOQItems || 1)) *
                        100
                    )
                  : 0}
                %
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-green-600 h-2 rounded-full"
                style={{
                  width: `${
                    (stats.totalBOQItems || 0) > 0
                      ? ((stats.itemsWithEntries || 0) /
                          (stats.totalBOQItems || 1)) *
                        100
                      : 0
                  }%`,
                }}
              ></div>
            </div>
            <div className="text-sm text-gray-500">
              {t("dashboard.itemsHaveConcentrationSheets", {
                withEntries: stats.itemsWithEntries || 0,
                total: stats.totalBOQItems || 0,
              })}
            </div>
          </div>
        </div>

        {/* System Info */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3
            className={`text-lg font-semibold text-gray-900 mb-4 flex items-center ${
              isRTL ? "flex-row-reverse" : ""
            }`}
          >
            <Building
              className={`h-5 w-5 text-purple-600 ${isRTL ? "ml-2" : "mr-2"}`}
            />
            <span>{t("dashboard.systemInfo")}</span>
          </h3>
          <div className="space-y-3 text-sm">
            <div
              className={`flex justify-between ${
                isRTL ? "flex-row-reverse" : ""
              }`}
            >
              <span className="text-gray-600">{t("dashboard.version")}:</span>
              <span
                className={`font-medium ${isRTL ? "text-left" : "text-right"}`}
              >
                1.0.0
              </span>
            </div>
            <div
              className={`flex justify-between ${
                isRTL ? "flex-row-reverse" : ""
              }`}
            >
              <span className="text-gray-600">
                {t("dashboard.lastUpdated")}:
              </span>
              <span
                className={`font-medium ${isRTL ? "text-left" : "text-right"}`}
              >
                {t("dashboard.today")}
              </span>
            </div>
            <div
              className={`flex justify-between ${
                isRTL ? "flex-row-reverse" : ""
              }`}
            >
              <span className="text-gray-600">{t("dashboard.database")}:</span>
              <span
                className={`font-medium ${isRTL ? "text-left" : "text-right"}`}
              >
                SQLite
              </span>
            </div>
            <div
              className={`flex justify-between ${
                isRTL ? "flex-row-reverse" : ""
              }`}
            >
              <span className="text-gray-600">{t("dashboard.backend")}:</span>
              <span
                className={`font-medium ${isRTL ? "text-left" : "text-right"}`}
              >
                FastAPI
              </span>
            </div>
          </div>
        </div>
      </div>

      <ReadApprovedSignedQtyModal
        isOpen={showApprovedSignedQtyModal}
        onClose={() => setShowApprovedSignedQtyModal(false)}
        onSuccess={handleApprovedSignedQtySuccess}
      />
    </div>
  );
};

export default Dashboard;
