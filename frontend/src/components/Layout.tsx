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
} from "lucide-react";
import { useTranslation } from "react-i18next";
import { useAuth } from "../contexts/AuthContext";
import { useLanguage } from "../contexts/LanguageContext";
import LanguageSwitcher from "./LanguageSwitcher";

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const location = useLocation();
  const { user, signout, isAuthenticated } = useAuth();
  const { isRTL, language } = useLanguage();
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [showUserMenu, setShowUserMenu] = useState(false);
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
        className={`fixed inset-y-0 z-50 w-64 bg-white shadow-lg flex flex-col ${
          isRTL ? "right-0 sidebar-rtl" : "left-0 sidebar-ltr"
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
          <LanguageSwitcher />
        </div>

        {/* Navigation */}
        <nav className="flex-1 mt-8 px-4">
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
                    {t("auth.profile")}
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
        className={`${isRTL ? "pr-64" : "pl-64"}`}
        style={{
          [isRTL ? "paddingRight" : "paddingLeft"]: "16rem", // 64 * 0.25rem = 16rem
          [isRTL ? "paddingLeft" : "paddingRight"]: "0px",
        }}
      >
        <main className="p-8">{children}</main>
      </div>
    </div>
  );
};

export default Layout;
