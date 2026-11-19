import React, { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { X } from "lucide-react";
import { useLanguage } from "../contexts/LanguageContext";

type Pending = {
  message: string;
  resolve: (answer: boolean) => void;
};

let openDialog: ((message: string) => Promise<boolean>) | null = null;

/** Yes or no. Resolves false when the dialog is not on screen. */
export function askYesNo(message: string): Promise<boolean> {
  if (!openDialog) return Promise.resolve(false);
  return openDialog(message);
}

/** Keep the question pinned under a long list so the buttons stay in view. */
function splitPrompt(message: string): { body: string; question: string | null } {
  const parts = message.split(/\n\n/);
  let questionIndex = -1;
  for (let i = parts.length - 1; i >= 0; i--) {
    if (parts[i].includes("?")) {
      questionIndex = i;
      break;
    }
  }
  if (questionIndex <= 0) return { body: message, question: null };
  const question = parts.slice(questionIndex).join("\n\n");
  if (question.length > 500) return { body: message, question: null };
  return {
    body: parts.slice(0, questionIndex).join("\n\n"),
    question,
  };
}

const YesNoDialog: React.FC = () => {
  const { t } = useTranslation();
  const { isRTL } = useLanguage();
  const [pending, setPending] = useState<Pending | null>(null);

  useEffect(() => {
    openDialog = (message: string) =>
      new Promise((resolve) => {
        setPending({ message, resolve });
      });
    return () => {
      openDialog = null;
    };
  }, []);

  useEffect(() => {
    if (!pending) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        const current = pending;
        setPending(null);
        current.resolve(false);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [pending]);

  if (!pending) return null;

  const answer = (value: boolean) => {
    const current = pending;
    setPending(null);
    current.resolve(value);
  };

  const { body, question } = splitPrompt(pending.message);

  return (
    <div className="fixed inset-0 z-[80] flex items-center justify-center bg-black/50 p-4">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="yes-no-dialog-body"
        className={`flex w-full max-w-lg flex-col rounded-lg bg-white shadow-xl ${
          isRTL ? "text-right" : "text-left"
        }`}
      >
        <div className="flex shrink-0 justify-end px-3 pt-3">
          <button
            type="button"
            onClick={() => answer(false)}
            className="rounded-md p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-700"
            aria-label={t("common.close")}
          >
            <X className="h-5 w-5" />
          </button>
        </div>
        <div
          className="overflow-y-auto px-6"
          style={{ maxHeight: "calc(100vh - 16rem)" }}
        >
          <p
            id="yes-no-dialog-body"
            className="whitespace-pre-wrap text-sm leading-6 text-gray-800"
          >
            {body}
          </p>
        </div>
        {question && (
          <p className="max-h-32 shrink-0 overflow-y-auto whitespace-pre-wrap px-6 pt-3 text-sm font-medium leading-6 text-gray-900">
            {question}
          </p>
        )}
        <div className="flex shrink-0 justify-end gap-3 px-6 py-4">
          <button
            type="button"
            onClick={() => answer(false)}
            className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            {t("common.no")}
          </button>
          <button
            type="button"
            onClick={() => answer(true)}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            {t("common.yes")}
          </button>
        </div>
      </div>
    </div>
  );
};

export default YesNoDialog;
