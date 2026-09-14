import React, { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useLanguage } from "../contexts/LanguageContext";
import { X } from "lucide-react";

interface CalculatorPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

const BUTTONS = [
  ["C", "CE", "⌫", "/"],
  ["7", "8", "9", "*"],
  ["4", "5", "6", "-"],
  ["1", "2", "3", "+"],
  ["±", "0", ".", "="],
];

function formatDisplay(value: string): string {
  if (!value || value === "-") return value || "0";
  const negative = value.startsWith("-");
  const raw = negative ? value.slice(1) : value;
  const [whole, fraction] = raw.split(".");
  const withCommas = whole.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  return `${negative ? "-" : ""}${withCommas}${
    fraction != null ? `.${fraction}` : ""
  }`;
}

const CalculatorPanel: React.FC<CalculatorPanelProps> = ({
  isOpen,
  onClose,
}) => {
  const { t } = useTranslation();
  const { isRTL } = useLanguage();
  const [display, setDisplay] = useState("0");
  const [accumulator, setAccumulator] = useState<number | null>(null);
  const [pendingOp, setPendingOp] = useState<string | null>(null);
  const [freshEntry, setFreshEntry] = useState(true);

  useEffect(() => {
    if (!isOpen) return;
    const onKey = (event: KeyboardEvent) => {
      const key = event.key;
      if (key === "Escape") {
        onClose();
        return;
      }
      if (/^[0-9.]$/.test(key)) {
        event.preventDefault();
        inputDigit(key);
        return;
      }
      if (["+", "-", "*", "/"].includes(key)) {
        event.preventDefault();
        applyOperator(key);
        return;
      }
      if (key === "Enter" || key === "=") {
        event.preventDefault();
        applyEquals();
        return;
      }
      if (key === "Backspace") {
        event.preventDefault();
        backspace();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  const currentNumber = () => parseFloat(display.replace(/,/g, "")) || 0;

  const inputDigit = (digit: string) => {
    setDisplay((prev) => {
      if (digit === "." && prev.includes(".")) return prev;
      if (freshEntry) {
        setFreshEntry(false);
        return digit === "." ? "0." : digit;
      }
      if (prev === "0" && digit !== ".") return digit;
      return `${prev}${digit}`;
    });
  };

  const compute = (left: number, right: number, op: string) => {
    switch (op) {
      case "+":
        return left + right;
      case "-":
        return left - right;
      case "*":
        return left * right;
      case "/":
        return right === 0 ? NaN : left / right;
      default:
        return right;
    }
  };

  const applyOperator = (op: string) => {
    const value = currentNumber();
    if (accumulator != null && pendingOp && !freshEntry) {
      const result = compute(accumulator, value, pendingOp);
      setAccumulator(result);
      setDisplay(Number.isFinite(result) ? String(result) : t("common.error"));
    } else {
      setAccumulator(value);
    }
    setPendingOp(op);
    setFreshEntry(true);
  };

  const applyEquals = () => {
    const value = currentNumber();
    if (accumulator == null || !pendingOp) return;
    const result = compute(accumulator, value, pendingOp);
    setDisplay(Number.isFinite(result) ? String(result) : t("common.error"));
    setAccumulator(null);
    setPendingOp(null);
    setFreshEntry(true);
  };

  const clearAll = () => {
    setDisplay("0");
    setAccumulator(null);
    setPendingOp(null);
    setFreshEntry(true);
  };

  const clearEntry = () => {
    setDisplay("0");
    setFreshEntry(true);
  };

  const backspace = () => {
    if (freshEntry) return;
    setDisplay((prev) => {
      const next = prev.slice(0, -1);
      return next === "" || next === "-" ? "0" : next;
    });
  };

  const negate = () => {
    setDisplay((prev) => {
      if (prev === "0") return prev;
      return prev.startsWith("-") ? prev.slice(1) : `-${prev}`;
    });
  };

  const handleButton = (label: string) => {
    if (label === "C") return clearAll();
    if (label === "CE") return clearEntry();
    if (label === "⌫") return backspace();
    if (label === "±") return negate();
    if (label === "=") return applyEquals();
    if (["+", "-", "*", "/"].includes(label)) return applyOperator(label);
    inputDigit(label);
  };

  if (!isOpen) return null;

  return (
    <div
      className={`fixed top-20 z-50 w-72 rounded-lg border border-gray-200 bg-white shadow-xl ${
        isRTL ? "left-4" : "right-4"
      }`}
      dir={isRTL ? "rtl" : "ltr"}
    >
      <div className="flex items-center justify-between px-3 py-2 border-b border-gray-200 bg-gray-50 rounded-t-lg">
        <h2 className="text-sm font-semibold text-gray-800">
          {t("common.calculator")}
        </h2>
        <button
          type="button"
          onClick={onClose}
          className="p-1 text-gray-500 hover:text-gray-800"
          aria-label={t("common.close")}
        >
          <X className="h-4 w-4" />
        </button>
      </div>
      <div className="p-3">
        <div className="mb-3 rounded-md bg-gray-900 text-white text-right px-3 py-3 text-2xl font-mono tracking-tight overflow-hidden">
          {formatDisplay(display)}
        </div>
        <div className="grid grid-cols-4 gap-2">
          {BUTTONS.flat().map((label) => (
            <button
              key={label}
              type="button"
              onClick={() => handleButton(label)}
              className={`h-11 rounded-md text-sm font-medium ${
                label === "="
                  ? "bg-blue-600 text-white hover:bg-blue-700"
                  : ["+", "-", "*", "/", "C", "CE", "⌫"].includes(label)
                    ? "bg-gray-200 text-gray-800 hover:bg-gray-300"
                    : "bg-gray-100 text-gray-900 hover:bg-gray-200"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};

export default CalculatorPanel;
