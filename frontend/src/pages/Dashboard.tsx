import React, { useState } from "react";
import { useQuery } from "react-query";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useLanguage } from "../contexts/LanguageContext";
import {
  boqApi,
  searchApi,
  concentrationApi,
  calculationSheetsApi,
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
} from "lucide-react";

const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const { isRTL } = useLanguage();
  const [selectedPeriod, setSelectedPeriod] = useState("all");

  // Fetch all necessary data
  const { data: boqItems, isLoading: boqLoading } = useQuery("boq-items", () =>
    boqApi.getAll()
  );
  const { data: summary, isLoading: summaryLoading } = useQuery("summary", () =>
    searchApi.getSummary()
  );
  const { data: concentrationSheets, isLoading: concentrationLoading } =
    useQuery("concentration-sheets", () => concentrationApi.getAll());
  const { data: calculationSheets, isLoading: calculationLoading } = useQuery(
    "calculation-sheets",
    () => calculationSheetsApi.getAll()
  );

  const isLoading =
    boqLoading || summaryLoading || concentrationLoading || calculationLoading;

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
      (sum, item) => sum + (item.total_approved_by_project_manager || 0),
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
      value: `$${(stats.totalContractValue || 0).toLocaleString()}`,
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
      value: `$${(stats.totalEstimateValue || 0).toLocaleString()}`,
      change: stats.estimateVariance || 0,
      changeType: (stats.estimateVariance || 0) >= 0 ? "positive" : "negative",
      progress: stats.estimateProgress || 0,
      icon: TrendingUp,
    },
    {
      name: t("dashboard.totalSubmitted"),
      value: `$${(stats.totalSubmittedValue || 0).toLocaleString()}`,
      change: stats.submittedVariance || 0,
      changeType: (stats.submittedVariance || 0) >= 0 ? "positive" : "negative",
      progress: stats.submittedProgress || 0,
      icon: Upload,
    },
    {
      name: t("dashboard.totalApproved"),
      value: `$${(stats.totalApprovedValue || 0).toLocaleString()}`,
      change: stats.approvedVariance || 0,
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

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className={`text-center ${isRTL ? "text-right" : "text-left"}`}>
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
        <div className={isRTL ? "text-right" : "text-left"}>
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
                    <p
                      className={`text-sm font-medium text-gray-600 ${
                        isRTL ? "text-right" : "text-left"
                      }`}
                    >
                      {stat.name}
                    </p>
                    <p
                      className={`text-2xl font-semibold text-gray-900 ${
                        isRTL ? "text-right" : "text-left"
                      }`}
                    >
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
              <p
                className={`text-xs text-gray-500 mt-3 ${
                  isRTL ? "text-right" : "text-left"
                }`}
              >
                {stat.description}
              </p>
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
                  <h3
                    className={`text-lg font-medium text-gray-900 ${
                      isRTL ? "text-right" : "text-left"
                    }`}
                  >
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
                  ${Math.abs(metric.change || 0).toLocaleString()}
                </div>
              </div>
              <p
                className={`text-3xl font-bold text-gray-900 mb-4 ${
                  isRTL ? "text-right" : "text-left"
                }`}
              >
                {metric.value}
              </p>

              {/* Progress bar */}
              <div className="mb-2">
                <div
                  className={`flex justify-between text-sm text-gray-600 mb-1 ${
                    isRTL ? "flex-row-reverse" : ""
                  }`}
                >
                  <span className={isRTL ? "text-right" : "text-left"}>
                    {t("dashboard.progress")}
                  </span>
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

              <p
                className={`text-xs text-gray-500 ${
                  isRTL ? "text-right" : "text-left"
                }`}
              >
                {metric.changeType === "positive"
                  ? t("dashboard.aboveContractValue")
                  : t("dashboard.belowContractValue")}
              </p>
            </div>
          );
        })}
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
              <span className={isRTL ? "text-right" : "text-left"}>
                {t("dashboard.subChaptersSummary")}
              </span>
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
                    <div className={isRTL ? "text-right" : "text-left"}>
                      <p
                        className={`font-medium text-gray-900 ${
                          isRTL ? "text-right" : "text-left"
                        }`}
                      >
                        {item.sub_chapter}
                      </p>
                      <p
                        className={`text-sm text-gray-600 ${
                          isRTL ? "text-right" : "text-left"
                        }`}
                      >
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
                    <button
                      className={`text-blue-600 hover:text-blue-800 text-sm font-medium ${
                        isRTL ? "text-right" : "text-left"
                      }`}
                    >
                      {t("dashboard.viewAllSubChapters", {
                        count: summary.summaries.length,
                      })}
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <div
                className={`text-center text-gray-500 py-8 ${
                  isRTL ? "text-right" : "text-left"
                }`}
              >
                <PieChart className="h-12 w-12 mx-auto mb-4 text-gray-300" />
                <p className={isRTL ? "text-right" : "text-left"}>
                  {t("dashboard.noSubChapterDataAvailable")}
                </p>
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
              <span className={isRTL ? "text-right" : "text-left"}>
                {t("dashboard.systemStatus")}
              </span>
            </h2>
          </div>
          <div className="p-6">
            <div className="space-y-4">
              <div className="flex items-center justify-between p-3 bg-green-50 rounded-lg border border-green-200">
                <div className="flex items-center">
                  <CheckCircle className="h-5 w-5 text-green-600 mr-3" />
                  <div className={isRTL ? "text-right" : "text-left"}>
                    <p
                      className={`font-medium text-green-900 ${
                        isRTL ? "text-right" : "text-left"
                      }`}
                    >
                      {t("dashboard.systemOperational")}
                    </p>
                    <p
                      className={`text-sm text-green-700 ${
                        isRTL ? "text-right" : "text-left"
                      }`}
                    >
                      {t("dashboard.allServicesRunningNormally")}
                    </p>
                  </div>
                </div>
                <span
                  className={`text-green-600 text-sm font-medium ${
                    isRTL ? "text-left" : "text-right"
                  }`}
                >
                  ✓ {t("dashboard.active")}
                </span>
              </div>

              <div className="flex items-center justify-between p-3 bg-blue-50 rounded-lg border border-blue-200">
                <div className="flex items-center">
                  <Package className="h-5 w-5 text-blue-600 mr-3" />
                  <div className={isRTL ? "text-right" : "text-left"}>
                    <p
                      className={`font-medium text-blue-900 ${
                        isRTL ? "text-right" : "text-left"
                      }`}
                    >
                      {t("dashboard.dataIntegrity")}
                    </p>
                    <p
                      className={`text-sm text-blue-700 ${
                        isRTL ? "text-right" : "text-left"
                      }`}
                    >
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
                  <div className={isRTL ? "text-right" : "text-left"}>
                    <p
                      className={`font-medium text-yellow-900 ${
                        isRTL ? "text-right" : "text-left"
                      }`}
                    >
                      {t("dashboard.pendingActions")}
                    </p>
                    <p
                      className={`text-sm text-yellow-700 ${
                        isRTL ? "text-right" : "text-left"
                      }`}
                    >
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
            <span className={isRTL ? "text-right" : "text-left"}>
              {t("dashboard.recentActivity")}
            </span>
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
                      <p
                        className={`text-sm font-medium text-gray-900 ${
                          isRTL ? "text-right" : "text-left"
                        }`}
                      >
                        {activity.message}
                      </p>
                      <p
                        className={`text-xs text-gray-500 ${
                          isRTL ? "text-right" : "text-left"
                        }`}
                      >
                        {activity.timestamp}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div
              className={`text-center text-gray-500 py-8 ${
                isRTL ? "text-right" : "text-left"
              }`}
            >
              <Clock className="h-12 w-12 mx-auto mb-4 text-gray-300" />
              <p className={isRTL ? "text-right" : "text-left"}>
                {t("dashboard.noRecentActivityDisplay")}
              </p>
              <p className={`text-sm ${isRTL ? "text-right" : "text-left"}`}>
                {t("dashboard.importBOQFileToGetStarted")}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Quick Actions */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2
            className={`text-lg font-semibold text-gray-900 ${
              isRTL ? "text-right" : "text-left"
            }`}
          >
            {t("dashboard.quickActions")}
          </h2>
        </div>
        <div className="p-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {quickActions.map((action) => {
              const Icon = action.icon;
              return (
                <button
                  key={action.name}
                  onClick={action.action}
                  className={`${action.color} text-white px-4 py-3 rounded-lg transition-all duration-200 transform hover:scale-105 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500`}
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
            <span className={isRTL ? "text-right" : "text-left"}>
              {t("dashboard.exportOptions")}
            </span>
          </h3>
          <div className="space-y-3">
            <button
              onClick={() => navigate("/boq")}
              className="w-full text-left p-3 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors cursor-pointer"
            >
              <div className="flex items-center justify-between">
                <span
                  className={`font-medium text-gray-900 ${
                    isRTL ? "text-right" : "text-left"
                  }`}
                >
                  {t("dashboard.boqSummaryReport")}
                </span>
                <Download className="h-4 w-4 text-gray-400" />
              </div>
              <p
                className={`text-sm text-gray-600 ${
                  isRTL ? "text-right" : "text-left"
                }`}
              >
                {t("dashboard.pdfSummaryAllBOQItems")}
              </p>
            </button>
            <button
              onClick={() => navigate("/concentration")}
              className="w-full text-left p-3 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors cursor-pointer"
            >
              <div className="flex items-center justify-between">
                <span
                  className={`font-medium text-gray-900 ${
                    isRTL ? "text-right" : "text-left"
                  }`}
                >
                  {t("dashboard.concentrationSheets")}
                </span>
                <Download className="h-4 w-4 text-gray-400" />
              </div>
              <p
                className={`text-sm text-gray-600 ${
                  isRTL ? "text-right" : "text-left"
                }`}
              >
                {t("dashboard.excelExportWithAllData")}
              </p>
            </button>
            <button
              onClick={() => navigate("/calculation-sheets")}
              className="w-full text-left p-3 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors cursor-pointer"
            >
              <div className="flex items-center justify-between">
                <span
                  className={`font-medium text-gray-900 ${
                    isRTL ? "text-right" : "text-left"
                  }`}
                >
                  {t("dashboard.calculationSheets")}
                </span>
                <Download className="h-4 w-4 text-gray-400" />
              </div>
              <p
                className={`text-sm text-gray-600 ${
                  isRTL ? "text-right" : "text-left"
                }`}
              >
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
            <span className={isRTL ? "text-right" : "text-left"}>
              {t("dashboard.performance")}
            </span>
          </h3>
          <div className="space-y-4">
            <div
              className={`flex justify-between items-center ${
                isRTL ? "flex-row-reverse" : ""
              }`}
            >
              <span
                className={`text-gray-600 ${
                  isRTL ? "text-right" : "text-left"
                }`}
              >
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
            <div
              className={`text-sm text-gray-500 ${
                isRTL ? "text-right" : "text-left"
              }`}
            >
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
            <span className={isRTL ? "text-right" : "text-left"}>
              {t("dashboard.systemInfo")}
            </span>
          </h3>
          <div className="space-y-3 text-sm">
            <div
              className={`flex justify-between ${
                isRTL ? "flex-row-reverse" : ""
              }`}
            >
              <span
                className={`text-gray-600 ${
                  isRTL ? "text-right" : "text-left"
                }`}
              >
                {t("dashboard.version")}:
              </span>
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
              <span
                className={`text-gray-600 ${
                  isRTL ? "text-right" : "text-left"
                }`}
              >
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
              <span
                className={`text-gray-600 ${
                  isRTL ? "text-right" : "text-left"
                }`}
              >
                {t("dashboard.database")}:
              </span>
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
              <span
                className={`text-gray-600 ${
                  isRTL ? "text-right" : "text-left"
                }`}
              >
                {t("dashboard.backend")}:
              </span>
              <span
                className={`font-medium ${isRTL ? "text-left" : "text-right"}`}
              >
                FastAPI
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
