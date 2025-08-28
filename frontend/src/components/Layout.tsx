import React from "react";
import { Link, useLocation } from "react-router-dom";
import { Home, FileText, Calculator, Upload, BarChart3 } from "lucide-react";

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const location = useLocation();

  const navigation = [
    { name: "Dashboard", href: "/", icon: Home },
    { name: "BOQ Items", href: "/boq", icon: FileText },
    { name: "Concentration Sheets", href: "/concentration", icon: Calculator },
    { name: "Calculation Sheets", href: "/calculation-sheets", icon: FileText },
    {
      name: "Summary of Subsections",
      href: "/summary-subsections",
      icon: BarChart3,
    },
    {
      name: "Summary of Systems",
      href: "/summary-systems",
      icon: BarChart3,
    },
    {
      name: "Summary of Structures",
      href: "/summary-structures",
      icon: BarChart3,
    },
    { name: "Import", href: "/import", icon: Upload },
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Sidebar */}
      <div className="fixed inset-y-0 left-0 z-50 w-64 bg-white shadow-lg">
        <div className="flex h-16 items-center justify-center border-b border-gray-200">
          <h1 className="text-xl font-bold text-gray-900">BOQ Management</h1>
        </div>

        <nav className="mt-8 px-4">
          <ul className="space-y-2">
            {navigation.map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname === item.href;

              return (
                <li key={item.name}>
                  <Link
                    to={item.href}
                    className={`flex items-center px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                      isActive
                        ? "bg-blue-100 text-blue-700 border-r-2 border-blue-700"
                        : "text-gray-600 hover:bg-gray-100 hover:text-gray-900"
                    }`}
                  >
                    <Icon className="mr-3 h-5 w-5" />
                    {item.name}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>
      </div>

      {/* Main content */}
      <div className="pl-64">
        <main className="p-8">{children}</main>
      </div>
    </div>
  );
};

export default Layout;
