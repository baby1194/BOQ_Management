import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../contexts/AuthContext";
import { useLanguage } from "../contexts/LanguageContext";
import { authApi } from "../services/api";
import { Eye, EyeOff, LogIn, UserPlus } from "lucide-react";
import toast from "react-hot-toast";
import LanguageSwitcher from "../components/LanguageSwitcher";

const SignIn: React.FC = () => {
  const [isSignUp, setIsSignUp] = useState(false);
  const [formData, setFormData] = useState({
    username: "",
    password: "",
    systemPassword: "",
    confirmPassword: "",
  });
  const [showPassword, setShowPassword] = useState(false);
  const [showSystemPassword, setShowSystemPassword] = useState(false);
  const [signupAllowed, setSignupAllowed] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [checkingSignupStatus, setCheckingSignupStatus] = useState(true);

  const { signin, signup, isAuthenticated } = useAuth();
  const { t } = useTranslation();
  // const { isRTL } = useLanguage();
  const navigate = useNavigate();

  useEffect(() => {
    // Check if signup is allowed
    const checkSignupAllowed = async () => {
      try {
        setCheckingSignupStatus(true);
        const response = await authApi.checkSignupAllowed();
        setSignupAllowed(response.signup_allowed);
        if (response.signup_allowed) {
          setIsSignUp(true);
        }
      } catch (error) {
        console.error("Failed to check signup status:", error);
        // If there's an error, assume signup is allowed (no user exists)
        setSignupAllowed(true);
        setIsSignUp(true);
      } finally {
        setCheckingSignupStatus(false);
      }
    };

    checkSignupAllowed();
  }, []);

  useEffect(() => {
    if (isAuthenticated) {
      navigate("/");
    }
  }, [isAuthenticated, navigate]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      if (isSignUp) {
        if (formData.password !== formData.confirmPassword) {
          toast.error(t("auth.passwordsDoNotMatch"));
          return;
        }
        if (formData.password.length < 6) {
          toast.error(t("auth.passwordTooShort"));
          return;
        }
        await signup(
          formData.username,
          formData.password,
          formData.systemPassword
        );
        toast.success(t("auth.signUpSuccess"));
      } else {
        await signin(formData.username, formData.password);
        toast.success(t("auth.signInSuccess"));
      }
    } catch (error: any) {
      toast.error(error.message || "Authentication failed");
    } finally {
      setIsLoading(false);
    }
  };

  const toggleMode = () => {
    if (signupAllowed || isSignUp) {
      setIsSignUp(!isSignUp);
      setFormData({
        username: "",
        password: "",
        systemPassword: "",
        confirmPassword: "",
      });
    }
  };

  if (checkingSignupStatus) {
    return (
      <div className="min-h-screen bg-gray-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
        <div className="sm:mx-auto sm:w-full sm:max-w-md">
          <div className="flex justify-center">
            <div className="w-12 h-12 bg-blue-600 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-xl">B</span>
            </div>
          </div>
          <div className="mt-6 text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
            <p className="mt-2 text-gray-600">{t("common.loading")}</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      className={`min-h-screen bg-gray-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8`}
    >
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="flex justify-between items-center">
          <div className="flex justify-center flex-1">
            <div className="w-12 h-12 bg-blue-600 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-xl">B</span>
            </div>
          </div>
          <LanguageSwitcher />
        </div>
        <h2
          className={`mt-6 text-center text-3xl font-extrabold text-gray-900`}
        >
          {isSignUp ? t("auth.createYourAccount") : t("auth.signInToAccount")}
        </h2>
        <p className={`mt-2 text-center text-sm text-gray-600`}>
          {t("common.systemTitle")}
        </p>
        {signupAllowed && isSignUp && (
          <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-md">
            <p className={`text-sm text-blue-700`}>
              {t("auth.noUserAccountFound")}
            </p>
          </div>
        )}
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-4 shadow sm:rounded-lg sm:px-10">
          <form className="space-y-6" onSubmit={handleSubmit}>
            <div>
              <label
                htmlFor="username"
                className={`block text-sm font-medium text-gray-700`}
              >
                {t("auth.username")}
              </label>
              <div className="mt-1">
                <input
                  id="username"
                  name="username"
                  type="text"
                  required
                  value={formData.username}
                  onChange={handleInputChange}
                  className={`appearance-none block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm`}
                  placeholder={t("auth.username")}
                />
              </div>
            </div>

            <div>
              <label
                htmlFor="password"
                className={`block text-sm font-medium text-gray-700`}
              >
                {t("auth.password")}
              </label>
              <div className="mt-1 relative">
                <input
                  id="password"
                  name="password"
                  type={showPassword ? "text" : "password"}
                  required
                  value={formData.password}
                  onChange={handleInputChange}
                  className={`appearance-none block w-full px-3 py-2 pr-10 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm`}
                  placeholder={t("auth.password")}
                />
                <button
                  type="button"
                  className={`absolute inset-y-0 right-0 pr-3 flex items-center`}
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

            {isSignUp && (
              <>
                <div>
                  <label
                    htmlFor="confirmPassword"
                    className={`block text-sm font-medium text-gray-700`}
                  >
                    {t("auth.confirmPassword")}
                  </label>
                  <div className="mt-1">
                    <input
                      id="confirmPassword"
                      name="confirmPassword"
                      type="password"
                      required={isSignUp}
                      value={formData.confirmPassword}
                      onChange={handleInputChange}
                      className={`appearance-none block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm`}
                      placeholder={t("auth.confirmPassword")}
                    />
                  </div>
                </div>

                <div>
                  <label
                    htmlFor="systemPassword"
                    className={`block text-sm font-medium text-gray-700`}
                  >
                    {t("auth.systemPassword")}
                  </label>
                  <div className="mt-1 relative">
                    <input
                      id="systemPassword"
                      name="systemPassword"
                      type={showSystemPassword ? "text" : "password"}
                      required={isSignUp}
                      value={formData.systemPassword}
                      onChange={handleInputChange}
                      className={`appearance-none block w-full px-3 py-2 pr-10 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm`}
                      placeholder={t("auth.systemPassword")}
                    />
                    <button
                      type="button"
                      className={`absolute inset-y-0 right-0 pr-3 flex items-center`}
                      onClick={() => setShowSystemPassword(!showSystemPassword)}
                    >
                      {showSystemPassword ? (
                        <EyeOff className="h-4 w-4 text-gray-400" />
                      ) : (
                        <Eye className="h-4 w-4 text-gray-400" />
                      )}
                    </button>
                  </div>
                  <p className={`mt-1 text-xs text-gray-500 `}>
                    {t("auth.systemPasswordRequired")}
                  </p>
                </div>
              </>
            )}

            <div>
              <button
                type="submit"
                disabled={isLoading}
                className="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? (
                  <span className="flex items-center">
                    <svg
                      className={`animate-spin -ml-1 mr-3 h-5 w-5 text-white`}
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
                    {t("common.loading")}
                  </span>
                ) : (
                  <span className="flex items-center">
                    {isSignUp ? (
                      <>
                        <UserPlus className={`w-4 h-4 mr-2}`} />
                        {t("auth.createAccount")}
                      </>
                    ) : (
                      <>
                        <LogIn className={`w-4 h-4 mr-2`} />
                        {t("auth.signIn")}
                      </>
                    )}
                  </span>
                )}
              </button>
            </div>

            {signupAllowed && (
              <div className="text-center">
                <button
                  type="button"
                  onClick={toggleMode}
                  className="text-sm text-blue-600 hover:text-blue-500"
                >
                  {isSignUp
                    ? t("auth.alreadyHaveAccount")
                    : t("auth.needAccount")}
                </button>
              </div>
            )}
          </form>
        </div>
      </div>
    </div>
  );
};

export default SignIn;
