import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import toast from "react-hot-toast";
import { drawingListApi } from "../services/api";

const WordItemsExport: React.FC<{ language: string }> = ({ language }) => {
  const { t } = useTranslation();
  const [words, setWords] = useState("");
  const [busy, setBusy] = useState(false);

  const download = async () => {
    try {
      setBusy(true);
      await drawingListApi.downloadWordItemsExcel(words, language);
    } catch {
      toast.error(t("concentration.wordItemsFailed"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mt-4 space-y-2">
      <label className="block text-sm font-medium text-gray-700">
        {t("concentration.wordsForItems")}
      </label>
      <p className="text-xs text-gray-500">{t("concentration.wordsForItemsHint")}</p>
      <textarea
        value={words}
        onChange={(event) => setWords(event.target.value)}
        rows={2}
        placeholder={t("concentration.wordsForItemsPlaceholder")}
        className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
      />
      <button
        type="button"
        onClick={() => void download()}
        disabled={busy || !words.trim()}
        className="bg-slate-700 text-white px-3 py-2 rounded-md text-sm disabled:opacity-50"
      >
        {busy
          ? t("concentration.downloadingWordItems")
          : t("concentration.downloadWordItems")}
      </button>
    </div>
  );
};

export default WordItemsExport;
