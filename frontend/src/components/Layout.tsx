import React, { useState, useEffect, useRef } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import {
  Home,
  FileText,
  Calculator,
  Upload,
  BarChart3,
  User,
  Settings,
  LogOut,
  Menu,
  X,
  Plus,
  FolderKanban,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import { useAuth } from "../contexts/AuthContext";
import { useLanguage } from "../contexts/LanguageContext";
import { useProject } from "../contexts/ProjectContext";
import LanguageSwitcher from "./LanguageSwitcher";
import NewProjectModal from "./NewProjectModal";

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const location = useLocation();
  const { user, signout, isAuthenticated } = useAuth();
  const { isRTL, language } = useLanguage();
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { projects, activeProject, switchProject, isLoading: projectsLoading } =
    useProject();
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [showNewProjectModal, setShowNewProjectModal] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  const handleSignOut = async () => {
    try {
      await signout();
      navigate("/signin");
    } catch (error) {
      console.error("Sign out error:", error);
    }
  };

  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setShowUserMenu(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  const navigation = [
    {
      name: t("navigation.dashboard"),
      href: "/",
      icon: Home,
      key: "dashboard",
    },
    {
      name: t("navigation.boqItems"),
      href: "/boq",
      icon: FileText,
      key: "boqItems",
    },
    {
      name: t("navigation.concentrationSheets"),
      href: "/concentration",
      icon: Calculator,
      key: "concentration",
    },
    {
      name: t("navigation.calculationSheets"),
      href: "/calculation-sheets",
      icon: FileText,
      key: "calculation",
    },
    {
      name: t("navigation.summarySubsections"),
      href: "/summary-subsections",
      icon: BarChart3,
      key: "summarySubsections",
    },
    {
      name: t("navigation.summarySystems"),
      href: "/summary-systems",
      icon: BarChart3,
      key: "summarySystems",
    },
    {
      name: t("navigation.summaryStructures"),
      href: "/summary-structures",
      icon: BarChart3,
      key: "summaryStructures",
    },
    {
      name: t("navigation.fileImport"),
      href: "/import",
      icon: Upload,
      key: "import",
    },
  ];

  return (
    <div className={`min-h-screen bg-gray-50 ${isRTL ? "rtl" : "ltr"}`}>
      {/* Sidebar */}
      <div
        className={`fixed inset-y-0 z-50 w-64 bg-white shadow-lg flex flex-col transition-transform duration-300 ease-in-out ${
          isRTL ? "right-0 sidebar-rtl" : "left-0 sidebar-ltr"
        } ${
          isSidebarOpen
            ? "translate-x-0"
            : isRTL
            ? "translate-x-full"
            : "-translate-x-full"
        }`}
        style={{
          [isRTL ? "right" : "left"]: "0px",
          [isRTL ? "left" : "right"]: "auto",
        }}
      >
        {/* Header */}
        <div className="flex h-16 items-center justify-between px-4 border-b border-gray-200">
          <h1
            className={`text-xl font-bold text-gray-900 ${
              isRTL ? "text-right" : "text-left"
            }`}
          >
            {t("common.appTitle")}
          </h1>
          <div className="flex items-center gap-2">
            <LanguageSwitcher />
            <button
              onClick={() => setIsSidebarOpen(!isSidebarOpen)}
              className="p-2 rounded-md text-gray-600 hover:bg-gray-100 hover:text-gray-900 transition-colors"
              aria-label={isSidebarOpen ? "Close sidebar" : "Open sidebar"}
            >
              {isSidebarOpen ? (
                <X className="h-5 w-5" />
              ) : (
                <Menu className="h-5 w-5" />
              )}
            </button>
          </div>
        </div>

        {/* Project selector */}
        {isAuthenticated && (
          <div className="px-4 py-4 border-b border-gray-200">
            <label
              htmlFor="project-select"
              className={`flex items-center text-xs font-medium text-gray-500 mb-2 ${
                isRTL ? "flex-row-reverse" : ""
              }`}
            >
              <FolderKanban className={`h-3.5 w-3.5 ${isRTL ? "ml-1.5" : "mr-1.5"}`} />
              {t("projects.currentProject")}
            </label>
            <select
              id="project-select"
              value={activeProject?.id ?? ""}
              onChange={(e) => switchProject(e.target.value)}
              disabled={projectsLoading || projects.length === 0}
              className={`w-full px-3 py-2 text-sm border border-gray-300 rounded-md bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                isRTL ? "text-right" : "text-left"
              }`}
            >
              {projects.length === 0 ? (
                <option value="">{t("projects.noProjects")}</option>
              ) : (
                projects.map((project) => (
                  <option key={project.id} value={project.id}>
                    {project.name}
                  </option>
                ))
              )}
            </select>
            <button
              onClick={() => setShowNewProjectModal(true)}
              className={`mt-2 w-full flex items-center justify-center px-3 py-2 text-sm font-medium text-blue-700 bg-blue-50 rounded-md hover:bg-blue-100 transition-colors ${
                isRTL ? "flex-row-reverse" : ""
              }`}
            >
              <Plus className={`h-4 w-4 ${isRTL ? "ml-2" : "mr-2"}`} />
              {t("projects.newProject")}
            </button>
          </div>
        )}

        {/* Navigation */}
        <nav className="flex-1 mt-4 px-4">
          <ul className="space-y-2">
            {navigation.map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname === item.href;

              return (
                <li key={item.key}>
                  <Link
                    to={item.href}
                    className={`flex items-center px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                      isActive
                        ? `bg-blue-100 text-blue-700 ${
                            isRTL
                              ? "border-l-2 border-blue-700"
                              : "border-r-2 border-blue-700"
                          }`
                        : "text-gray-600 hover:bg-gray-100 hover:text-gray-900"
                    }`}
                  >
                    <Icon className={`${isRTL ? "ml-3" : "mr-3"} h-5 w-5`} />
                    {item.name}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>

        {/* User menu at bottom of sidebar */}
        {isAuthenticated && user && (
          <div className="p-4 border-t border-gray-200" ref={menuRef}>
            <div className="relative">
              <button
                onClick={() => setShowUserMenu(!showUserMenu)}
                className={`w-full flex items-center px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                  location.pathname === "/profile"
                    ? `bg-blue-100 text-blue-700 ${
                        isRTL
                          ? "border-l-2 border-blue-700"
                          : "border-r-2 border-blue-700"
                      }`
                    : "text-gray-600 hover:bg-gray-100 hover:text-gray-900"
                }`}
              >
                <div
                  className={`w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center ${
                    isRTL ? "ml-3" : "mr-3"
                  }`}
                >
                  <User className="w-4 h-4 text-white" />
                </div>
                <div className={`flex-1 ${isRTL ? "text-right" : "text-left"}`}>
                  <p className="text-sm font-medium">{user.username}</p>
                  <p className="text-xs text-gray-500">
                    {t("navigation.profile")}
                  </p>
                </div>
              </button>

              {showUserMenu && (
                <div
                  className={`absolute bottom-full ${
                    isRTL ? "right-0" : "left-0"
                  } mb-2 w-full bg-white rounded-lg shadow-lg border border-gray-200 py-1`}
                >
                  <Link
                    to="/profile"
                    className={`flex items-center px-4 py-2 text-sm text-gray-700 hover:bg-gray-100`}
                    onClick={() => setShowUserMenu(false)}
                  >
                    <Settings
                      className={`w-4 h-4 ${isRTL ? "ml-3" : "mr-3"}`}
                    />
                    {t("navigation.profile")}
                  </Link>
                  <button
                    onClick={handleSignOut}
                    className={`w-full flex items-center px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 ${
                      isRTL ? "text-right" : "text-left"
                    }`}
                  >
                    <LogOut className={`w-4 h-4 ${isRTL ? "ml-3" : "mr-3"}`} />
                    {t("navigation.signOut")}
                  </button>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Main content */}
      <div
        className={`transition-all duration-300 ease-in-out ${
          isSidebarOpen ? (isRTL ? "pr-64" : "pl-64") : ""
        }`}
        style={{
          [isRTL ? "paddingRight" : "paddingLeft"]: isSidebarOpen
            ? "16rem"
            : "0px", // 64 * 0.25rem = 16rem
          [isRTL ? "paddingLeft" : "paddingRight"]: "0px",
        }}
      >
        {/* Toggle button when sidebar is closed */}
        {!isSidebarOpen && (
          <button
            onClick={() => setIsSidebarOpen(true)}
            className={`fixed top-4 z-40 p-2 rounded-md bg-white shadow-lg text-gray-600 hover:bg-gray-100 hover:text-gray-900 transition-colors ${
              isRTL ? "right-4" : "left-4"
            }`}
            aria-label="Open sidebar"
          >
            <Menu className="h-5 w-5" />
          </button>
        )}
        <main className="p-8">{children}</main>
      </div>

      <NewProjectModal
        isOpen={showNewProjectModal}
        onClose={() => setShowNewProjectModal(false)}
      />
    </div>
  );
};

export default Layout;
