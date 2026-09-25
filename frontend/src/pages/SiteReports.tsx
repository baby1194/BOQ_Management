import React, { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import toast from "react-hot-toast";
import { ClipboardList, Trash2 } from "lucide-react";
import { siteWorkApi, SiteWorkItem } from "../services/api";

const SiteReports: React.FC = () => {
  const { t } = useTranslation();
  const [items, setItems] = useState<SiteWorkItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [source, setSource] = useState<"site_report" | "whatsapp">("site_report");
  const [workDate, setWorkDate] = useState("");
  const [text, setText] = useState("");
  const [photos, setPhotos] = useState<File[]>([]);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      setItems(await siteWorkApi.getAll());
    } catch {
      toast.error(t("siteWork.loadFailed"));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    load();
  }, [load]);

  const classificationLabel = (value: SiteWorkItem["classification"]) => {
    if (value === "exception") return t("siteWork.exception");
    if (value === "additional_work") return t("siteWork.additionalWork");
    return t("siteWork.systemWork");
  };

  const sourceLabel = (value: SiteWorkItem["source"]) =>
    value === "whatsapp" ? t("siteWork.whatsapp") : t("siteWork.siteReport");

  const onProcess = async () => {
    const form = new FormData();
    form.append("source", source);
    form.append("text", text);
    if (workDate) form.append("work_date", workDate);
    if (source === "whatsapp") {
      photos.forEach((file) => form.append("photos", file));
    }
    try {
      setProcessing(true);
      const result = await siteWorkApi.ingest(form);
      if (result.created_count === 0 && result.skipped_duplicates === 0) {
        toast.error(t("siteWork.noneFound"));
      } else {
        toast.success(
          t("siteWork.created", {
            count: result.created_count,
            skipped: result.skipped_duplicates,
          })
        );
        setText("");
        setPhotos([]);
      }
      await load();
    } catch {
      toast.error(t("siteWork.processFailed"));
    } finally {
      setProcessing(false);
    }
  };

  const onDelete = async (id: number) => {
    try {
      await siteWorkApi.delete(id);
      setItems((current) => current.filter((item) => item.id !== id));
      toast.success(t("siteWork.deleted"));
    } catch {
      toast.error(t("siteWork.processFailed"));
    }
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center gap-3">
        <ClipboardList className="h-7 w-7 text-blue-600" />
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">{t("siteWork.title")}</h1>
          <p className="text-sm text-gray-500">{t("siteWork.subtitle")}</p>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow p-4 space-y-4">
        <div className="flex flex-wrap gap-2">
          {(["site_report", "whatsapp"] as const).map((option) => (
            <button
              key={option}
              type="button"
              onClick={() => setSource(option)}
              className={`px-4 py-2 rounded-md text-sm font-medium ${
                source === option
                  ? "bg-blue-600 text-white"
                  : "bg-gray-100 text-gray-700"
              }`}
            >
              {option === "whatsapp" ? t("siteWork.whatsapp") : t("siteWork.siteReport")}
            </button>
          ))}
        </div>
        <label className="block text-sm text-gray-700">
          {t("siteWork.date")}
          <input
            type="date"
            value={workDate}
            onChange={(event) => setWorkDate(event.target.value)}
            className="mt-1 block border border-gray-300 rounded-md px-3 py-2"
          />
        </label>
        <label className="block text-sm text-gray-700">
          {t("siteWork.text")}
          <textarea
            value={text}
            onChange={(event) => setText(event.target.value)}
            rows={6}
            placeholder={t("siteWork.textPlaceholder")}
            className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2"
          />
        </label>
        {source === "whatsapp" && (
          <label className="block text-sm text-gray-700">
            {t("siteWork.photos")}
            <input
              type="file"
              accept="image/jpeg,image/png,image/webp,image/gif"
              multiple
              onChange={(event) => setPhotos(Array.from(event.target.files || []))}
              className="mt-1 block w-full text-sm"
            />
          </label>
        )}
        <button
          type="button"
          onClick={onProcess}
          disabled={processing || !text.trim()}
          className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm disabled:opacity-50"
        >
          {processing ? t("siteWork.processing") : t("siteWork.process")}
        </button>
      </div>

      <div className="bg-white rounded-lg shadow overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead className="bg-gray-50 text-gray-600">
            <tr>
              <th className="px-3 py-2 text-start">{t("siteWork.text")}</th>
              <th className="px-3 py-2 text-start">{t("siteWork.system")}</th>
              <th className="px-3 py-2 text-start">{t("siteWork.classification")}</th>
              <th className="px-3 py-2 text-start">{t("siteWork.source")}</th>
              <th className="px-3 py-2 text-start">{t("siteWork.date")}</th>
              <th className="px-3 py-2 text-start">{t("siteWork.photosCol")}</th>
              <th className="px-3 py-2" />
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={7} className="px-3 py-6 text-center text-gray-500">
                  {t("projects.loading")}
                </td>
              </tr>
            ) : items.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-3 py-6 text-center text-gray-500">
                  {t("siteWork.empty")}
                </td>
              </tr>
            ) : (
              items.map((item) => (
                <tr key={item.id} className="border-t border-gray-100">
                  <td className="px-3 py-2">{item.description}</td>
                  <td className="px-3 py-2">{item.system_name || "—"}</td>
                  <td className="px-3 py-2">{classificationLabel(item.classification)}</td>
                  <td className="px-3 py-2">{sourceLabel(item.source)}</td>
                  <td className="px-3 py-2">{item.work_date || "—"}</td>
                  <td className="px-3 py-2">
                    <div className="flex gap-2">
                      {(item.photo_paths || []).map((path) => (
                        <a key={path} href={path} target="_blank" rel="noreferrer">
                          <img src={path} alt="" className="h-10 w-10 object-cover rounded" />
                        </a>
                      ))}
                    </div>
                  </td>
                  <td className="px-3 py-2">
                    <button
                      type="button"
                      onClick={() => onDelete(item.id)}
                      className="text-red-600"
                      aria-label={t("siteWork.delete")}
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default SiteReports;
