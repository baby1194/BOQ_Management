import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { useLanguage } from "../contexts/LanguageContext";
import { useAuth } from "../contexts/AuthContext";
import { Eye, EyeOff, User, Key, Save } from "lucide-react";
import toast from "react-hot-toast";

const Profile: React.FC = () => {
  const { user, updateProfile, signout } = useAuth();
  const { t } = useTranslation();
  const { isRTL } = useLanguage();
  const [formData, setFormData] = useState({
    password: "",
    systemPassword: "",
    confirmPassword: "",
  });
  const [showPassword, setShowPassword] = useState(false);
  const [showSystemPassword, setShowSystemPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (formData.password && formData.password !== formData.confirmPassword) {
      toast.error(t("profile.passwordsDoNotMatch"));
      return;
    }

    if (formData.password && formData.password.length < 6) {
      toast.error(t("profile.passwordTooShort"));
      return;
    }

    if (!formData.password && !formData.systemPassword) {
      toast.error(t("profile.provideAtLeastOnePassword"));
      return;
    }

    setIsLoading(true);

    try {
      await updateProfile(
        formData.password || undefined,
        formData.systemPassword || undefined
      );

      setFormData({
        password: "",
        systemPassword: "",
        confirmPassword: "",
      });

      toast.success(t("profile.profileUpdatedSuccessfully"));
    } catch (error: any) {
      toast.error(error.message || t("profile.failedToUpdateProfile"));
    } finally {
      setIsLoading(false);
    }
  };

  const handleSignOut = async () => {
    try {
      await signout();
      toast.success(t("profile.signedOutSuccessfully"));
    } catch (error: any) {
      toast.error(error.message || t("profile.failedToSignOut"));
    }
  };

  if (!user) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className={`text-center ${isRTL ? "text-right" : "text-left"}`}>
          <p className="text-gray-500">{t("profile.noUserDataAvailable")}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto p-6">
      <div className="bg-white shadow rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <div className="flex items-center mb-6">
            <div className="flex-shrink-0">
              <div className="w-12 h-12 bg-blue-600 rounded-full flex items-center justify-center">
                <User className="w-6 h-6 text-white" />
              </div>
            </div>
            <div className={`${isRTL ? "mr-4" : "ml-4"}`}>
              <h1
                className={`text-2xl font-bold text-gray-900 ${
                  isRTL ? "text-right" : "text-left"
                }`}
              >
                {t("profile.title")}
              </h1>
              <p
                className={`text-gray-600 ${
                  isRTL ? "text-right" : "text-left"
                }`}
              >
                {t("profile.manageAccountSettings")}
              </p>
            </div>
          </div>

          {/* User Information */}
          <div className="mb-8">
            <h3
              className={`text-lg font-medium text-gray-900 mb-4 ${
                isRTL ? "text-right" : "text-left"
              }`}
            >
              {t("profile.accountInformation")}
            </h3>
            <div className="bg-gray-50 rounded-lg p-4">
              <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div>
                  <dt className="text-sm font-medium text-gray-500">
                    Username
                  </dt>
                  <dd className="mt-1 text-sm text-gray-900">
                    {user.username}
                  </dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-gray-500">Status</dt>
                  <dd className="mt-1">
                    <span
                      className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                        user.is_active
                          ? "bg-green-100 text-green-800"
                          : "bg-red-100 text-red-800"
                      }`}
                    >
                      {user.is_active ? "Active" : "Inactive"}
                    </span>
                  </dd>
                </div>
              </dl>
            </div>
          </div>

          {/* Password Update Form */}
          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-4 flex items-center">
                <Key className="w-5 h-5 mr-2" />
                Update Passwords
              </h3>
              <p className="text-sm text-gray-600 mb-6">
                Leave fields empty if you don't want to change them.
              </p>
            </div>

            <div>
              <label
                htmlFor="password"
                className="block text-sm font-medium text-gray-700"
              >
                New Password
              </label>
              <div className="mt-1 relative">
                <input
                  id="password"
                  name="password"
                  type={showPassword ? "text" : "password"}
                  value={formData.password}
                  onChange={handleInputChange}
                  className="appearance-none block w-full px-3 py-2 pr-10 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                  placeholder="Enter new password (min 6 characters)"
                />
                <button
                  type="button"
                  className="absolute inset-y-0 right-0 pr-3 flex items-center"
                  onClick={() => setShowPassword(!showPassword)}
                >
                  {showPassword ? (
                    <EyeOff className="h-4 w-4 text-gray-400" />
                  ) : (
                    <Eye className="h-4 w-4 text-gray-400" />
                  )}
                </button>
              </div>
            </div>

            {formData.password && (
              <div>
                <label
                  htmlFor="confirmPassword"
                  className="block text-sm font-medium text-gray-700"
                >
                  Confirm New Password
                </label>
                <div className="mt-1 relative">
                  <input
                    id="confirmPassword"
                    name="confirmPassword"
                    type={showConfirmPassword ? "text" : "password"}
                    value={formData.confirmPassword}
                    onChange={handleInputChange}
                    className="appearance-none block w-full px-3 py-2 pr-10 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                    placeholder="Confirm new password"
                  />
                  <button
                    type="button"
                    className="absolute inset-y-0 right-0 pr-3 flex items-center"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  >
                    {showConfirmPassword ? (
                      <EyeOff className="h-4 w-4 text-gray-400" />
                    ) : (
                      <Eye className="h-4 w-4 text-gray-400" />
                    )}
                  </button>
                </div>
              </div>
            )}

            <div>
              <label
                htmlFor="systemPassword"
                className="block text-sm font-medium text-gray-700"
              >
                System Password
              </label>
              <div className="mt-1 relative">
                <input
                  id="systemPassword"
                  name="systemPassword"
                  type={showSystemPassword ? "text" : "password"}
                  value={formData.systemPassword}
                  onChange={handleInputChange}
                  className="appearance-none block w-full px-3 py-2 pr-10 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                  placeholder="Enter new system password (for BOQ operations)"
                />
                <button
                  type="button"
                  className="absolute inset-y-0 right-0 pr-3 flex items-center"
                  onClick={() => setShowSystemPassword(!showSystemPassword)}
                >
                  {showSystemPassword ? (
                    <EyeOff className="h-4 w-4 text-gray-400" />
                  ) : (
                    <Eye className="h-4 w-4 text-gray-400" />
                  )}
                </button>
              </div>
              <p className="mt-1 text-xs text-gray-500">
                This password is used for BOQ item operations (create, update,
                delete)
              </p>
            </div>

            <div className="flex justify-between items-center pt-6 border-t border-gray-200">
              <button
                type="submit"
                disabled={isLoading}
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? (
                  <span className="flex items-center">
                    <svg
                      className="animate-spin -ml-1 mr-3 h-4 w-4 text-white"
                      xmlns="http://www.w3.org/2000/svg"
                      fill="none"
                      viewBox="0 0 24 24"
                    >
                      <circle
                        className="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="4"
                      ></circle>
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                      ></path>
                    </svg>
                    Updating...
                  </span>
                ) : (
                  <span className="flex items-center">
                    <Save className="w-4 h-4 mr-2" />
                    Update Profile
                  </span>
                )}
              </button>

              <button
                type="button"
                onClick={handleSignOut}
                className="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md shadow-sm text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                Sign Out
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default Profile;
