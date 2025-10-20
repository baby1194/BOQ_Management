import React from "react";
import { useTranslation } from "react-i18next";
import { useLanguage } from "../contexts/LanguageContext";
import { Languages } from "lucide-react";

const LanguageSwitcher: React.FC = () => {
  const { i18n } = useTranslation();
  const { language, setLanguage, isRTL } = useLanguage();

  const languages = [
    { code: "en", name: "English", flag: "🇺🇸" },
    { code: "he", name: "עברית", flag: "🇮🇱" },
  ];

  const handleLanguageChange = (langCode: string) => {
    setLanguage(langCode);
  };

  return (
    <div className="relative inline-block text-left">
      <div className="flex items-center space-x-2">
        <Languages className="w-4 h-4" />
        <select
          value={language}
          onChange={(e) => handleLanguageChange(e.target.value)}
          className="bg-white border border-gray-300 rounded-md px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        >
          {languages.map((lang) => (
            <option key={lang.code} value={lang.code}>
              {lang.flag} {lang.name}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
};

export default LanguageSwitcher;
