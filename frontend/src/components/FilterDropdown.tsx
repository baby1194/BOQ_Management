import React, { useState, useRef, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useLanguage } from "../contexts/LanguageContext";

interface FilterDropdownProps {
  columnName: string;
  values: string[];
  selectedValues: string[];
  onSelectionChange: (selectedValues: string[]) => void;
  onClearFilter: () => void;
  isOpen: boolean;
  onToggle: () => void;
  onClose: () => void;
}

const FilterDropdown: React.FC<FilterDropdownProps> = ({
  columnName,
  values,
  selectedValues,
  onSelectionChange,
  onClearFilter,
  isOpen,
  onToggle,
  onClose,
}) => {
  const { t } = useTranslation();
  const { isRTL } = useLanguage();
  const [searchTerm, setSearchTerm] = useState("");
  const [dropdownPosition, setDropdownPosition] = useState({ top: 0, left: 0 });
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside and handle positioning
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        onClose();
      }
    };

    const handleScroll = () => {
      // Close dropdown on scroll to avoid positioning issues
      if (isOpen) {
        onClose();
      }
    };

    const handleResize = () => {
      // Close dropdown on resize to avoid positioning issues
      if (isOpen) {
        onClose();
      }
    };

    const handleKeyDown = (event: KeyboardEvent) => {
      // Close dropdown on Escape key
      if (event.key === "Escape" && isOpen) {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      document.addEventListener("keydown", handleKeyDown);
      window.addEventListener("scroll", handleScroll, true);
      window.addEventListener("resize", handleResize);
    }

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleKeyDown);
      window.removeEventListener("scroll", handleScroll, true);
      window.removeEventListener("resize", handleResize);
    };
  }, [isOpen, onClose]);

  // Update dropdown position when it opens
  useEffect(() => {
    if (isOpen && dropdownRef.current) {
      const rect = dropdownRef.current.getBoundingClientRect();
      const dropdownWidth = 256; // w-64 = 16rem = 256px
      const dropdownHeight = 300; // Approximate height

      let top = rect.bottom + 4;
      let left = rect.left;

      // Adjust if dropdown would go off the right edge
      if (left + dropdownWidth > window.innerWidth) {
        left = window.innerWidth - dropdownWidth - 10;
      }

      // Adjust if dropdown would go off the bottom edge
      if (top + dropdownHeight > window.innerHeight) {
        top = rect.top - dropdownHeight - 4;
      }

      // Ensure dropdown doesn't go off the left edge
      if (left < 10) {
        left = 10;
      }

      // Ensure dropdown doesn't go off the top edge
      if (top < 10) {
        top = 10;
      }

      setDropdownPosition({ top, left });
    }
  }, [isOpen]);

  // Filter values based on search term
  const filteredValues = values.filter((value) =>
    value.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleSelectAll = () => {
    if (selectedValues.length === filteredValues.length) {
      // Deselect all filtered values
      const newSelection = selectedValues.filter(
        (val) => !filteredValues.includes(val)
      );
      onSelectionChange(newSelection);
    } else {
      // Select all filtered values
      const newSelection = [...new Set([...selectedValues, ...filteredValues])];
      onSelectionChange(newSelection);
    }
  };

  const handleValueToggle = (value: string) => {
    if (selectedValues.includes(value)) {
      onSelectionChange(selectedValues.filter((v) => v !== value));
    } else {
      onSelectionChange([...selectedValues, value]);
    }
  };

  const isAllSelected =
    filteredValues.length > 0 &&
    filteredValues.every((value) => selectedValues.includes(value));
  const isPartiallySelected =
    filteredValues.some((value) => selectedValues.includes(value)) &&
    !isAllSelected;

  return (
    <div className="relative inline-block" ref={dropdownRef}>
      {/* Filter Icon Button */}
      <button
        onClick={onToggle}
        className={`p-1 rounded hover:bg-gray-200 transition-colors ${
          selectedValues.length > 0 ? "text-blue-600" : "text-gray-400"
        }`}
        title={`${t("common.filter")} ${columnName}`}
      >
        <svg
          className="w-4 h-4"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z"
          />
        </svg>
      </button>

      {/* Dropdown Menu - Using fixed positioning to avoid clipping */}
      {isOpen && (
        <div
          className="fixed w-64 bg-white border border-gray-300 rounded-md shadow-xl z-[9999]"
          dir={isRTL ? "rtl" : "ltr"}
          style={{
            top: dropdownPosition.top,
            left: dropdownPosition.left,
          }}
        >
          {/* Header */}
          <div className="px-3 py-2 border-b border-gray-200 bg-gray-50">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-medium text-gray-700">
                {t("common.filter")} {columnName}
              </h3>
              <button
                onClick={onClearFilter}
                className="text-xs text-red-600 hover:text-red-800"
              >
                {t("common.clearFilter")}
              </button>
            </div>
          </div>

          {/* Search Box */}
          <div className="px-3 py-2 border-b border-gray-200">
            <input
              type="text"
              placeholder={t("common.search")}
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          {/* Select All Option */}
          <div className="px-3 py-1 border-b border-gray-200">
            <label className="flex items-center space-x-2 cursor-pointer">
              <input
                type="checkbox"
                checked={isAllSelected}
                ref={(input) => {
                  if (input) input.indeterminate = isPartiallySelected;
                }}
                onChange={handleSelectAll}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="text-sm font-medium text-gray-700">
                ({t("common.selectAll")})
              </span>
            </label>
          </div>

          {/* Values List */}
          <div className="max-h-48 overflow-y-auto">
            {filteredValues.length === 0 ? (
              <div className="px-3 py-2 text-sm text-gray-500 text-center">
                {t("common.noValuesFound")}
              </div>
            ) : (
              filteredValues.map((value) => (
                <div key={value} className="px-3 py-1 hover:bg-gray-50">
                  <label className="flex items-center space-x-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={selectedValues.includes(value)}
                      onChange={() => handleValueToggle(value)}
                      className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <span
                      className="text-sm text-gray-700 truncate"
                      title={value}
                    >
                      {value || `(${t("common.empty")})`}
                    </span>
                  </label>
                </div>
              ))
            )}
          </div>

          {/* Footer */}
          <div className="px-3 py-2 border-t border-gray-200 bg-gray-50 flex justify-end space-x-2">
            <button
              onClick={onClose}
              className="px-3 py-1 text-sm text-gray-600 hover:text-gray-800"
            >
              {t("common.cancel")}
            </button>
            <button
              onClick={onClose}
              className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              {t("common.ok")}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default FilterDropdown;
