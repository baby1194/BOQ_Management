import React, { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import axios from "axios";
import toast from "react-hot-toast";
import { Link } from "react-router-dom";
import { ClipboardList, FileText, Trash2 } from "lucide-react";
import { siteWorkApi, SiteWorkItem } from "../services/api";

const SiteReports: React.FC = () => {
  const { t } = useTranslation();
  const [items, setItems] = useState<SiteWorkItem[]>([]);
  const [systems, setSystems] = useState<string[]>(["Exception"]);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [source, setSource] = useState<"site_report" | "whatsapp">("site_report");
  const [workDate, setWorkDate] = useState("");
  const [text, setText] = useState("");
  const [photos, setPhotos] = useState<File[]>([]);
  const [manualDescription, setManualDescription] = useState("");
  const [manualSystem, setManualSystem] = useState("Exception");
  const [manualClassification, setManualClassification] =
    useState<SiteWorkItem["classification"]>("exception");
  const [manualSource, setManualSource] = useState<SiteWorkItem["source"]>("site_report");
  const [manualDate, setManualDate] = useState("");
  const [adding, setAdding] = useState(false);
  const [filterSystem, setFilterSystem] = useState("");
  const [filterClassification, setFilterClassification] = useState("");
  const [filterSource, setFilterSource] = useState("");
  const [filterDate, setFilterDate] = useState("");
  const [noteDrafts, setNoteDrafts] = useState<Record<number, string>>({});

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const [rows, names] = await Promise.all([
        siteWorkApi.getAll(),
        siteWorkApi.systems(),
      ]);
      setItems(rows);
      setSystems(names.length ? names : ["Exception"]);
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
    photos.forEach((file) => form.append("photos", file));
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

  const onAdd = async () => {
    try {
      setAdding(true);
      const created = await siteWorkApi.create({
        description: manualDescription,
        system_name: manualSystem,
        classification: manualClassification,
        source: manualSource,
        work_date: manualDate || undefined,
      });
      setItems((current) => [created, ...current]);
      setManualDescription("");
      toast.success(t("siteWork.added"));
    } catch (error) {
      if (axios.isAxiosError(error) && error.response?.status === 409) {
        toast.error(t("siteWork.alreadyListed"));
      } else {
        toast.error(t("siteWork.processFailed"));
      }
    } finally {
      setAdding(false);
    }
  };

  const onSystemChange = async (item: SiteWorkItem, systemName: string) => {
    if (!systemName || systemName === (item.system_name || "")) return;
    try {
      const updated = await siteWorkApi.updateSystem(item.id, systemName);
      setItems((current) => current.map((row) => (row.id === item.id ? updated : row)));
    } catch {
      toast.error(t("siteWork.processFailed"));
    }
  };

  const onNotesBlur = async (item: SiteWorkItem) => {
    if (!(item.id in noteDrafts)) return;
    const next = noteDrafts[item.id];
    if (next === (item.notes || "")) {
      setNoteDrafts((current) => {
        const copy = { ...current };
        delete copy[item.id];
        return copy;
      });
      return;
    }
    try {
      const updated = await siteWorkApi.updateNotes(item.id, next);
      setItems((current) => current.map((row) => (row.id === item.id ? updated : row)));
      setNoteDrafts((current) => {
        const copy = { ...current };
        delete copy[item.id];
        return copy;
      });
    } catch {
      toast.error(t("siteWork.processFailed"));
    }
  };

  const onOpenAttachment = async (itemId: number, path: string) => {
    try {
      await siteWorkApi.openFile(itemId, path);
    } catch (error) {
      const detail = axios.isAxiosError(error) ? error.response?.data?.detail : null;
      toast.error(typeof detail === "string" ? detail : t("siteWork.openFailed"));
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

  const systemFilterOptions = Array.from(
    new Set([...systems, ...items.map((item) => item.system_name || "").filter(Boolean)])
  );

  const visibleItems = items.filter((item) => {
    if (filterSystem && (item.system_name || "") !== filterSystem) return false;
    if (filterClassification && item.classification !== filterClassification) return false;
    if (filterSource && item.source !== filterSource) return false;
    if (filterDate && (item.work_date || "") !== filterDate) return false;
    return true;
  });

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
              onClick={() => {
                setSource(option);
                setPhotos([]);
              }}
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
        <p className="text-sm text-gray-600">
          {source === "whatsapp" ? t("siteWork.whatsappHelp") : t("siteWork.reportHelp")}
        </p>
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
        {source === "whatsapp" ? (
          <label className="block text-sm text-gray-700">
            {t("siteWork.photos")}
            <input
              key="whatsapp-photos"
              type="file"
              accept="image/jpeg,image/png,image/webp,image/gif"
              multiple
              onChange={(event) => setPhotos(Array.from(event.target.files || []))}
              className="mt-1 block w-full text-sm"
            />
          </label>
        ) : (
          <label className="block text-sm text-gray-700">
            {t("siteWork.reportPdf")}
            <input
              key="site-report-pdf"
              type="file"
              accept="application/pdf,.pdf"
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

      <div className="bg-white rounded-lg shadow p-4 space-y-4">
        <h2 className="text-lg font-medium text-gray-900">{t("siteWork.addTask")}</h2>
        <label className="block text-sm text-gray-700">
          {t("siteWork.description")}
          <input
            value={manualDescription}
            onChange={(event) => setManualDescription(event.target.value)}
            className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2"
          />
        </label>
        <div className="flex flex-wrap gap-4">
          <label className="block text-sm text-gray-700">
            {t("siteWork.system")}
            <select
              value={manualSystem}
              onChange={(event) => setManualSystem(event.target.value)}
              className="mt-1 block border border-gray-300 rounded-md px-3 py-2 bg-white"
            >
              {systems.map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
            </select>
          </label>
          <label className="block text-sm text-gray-700">
            {t("siteWork.classification")}
            <select
              value={manualClassification}
              onChange={(event) =>
                setManualClassification(event.target.value as SiteWorkItem["classification"])
              }
              className="mt-1 block border border-gray-300 rounded-md px-3 py-2 bg-white"
            >
              <option value="system">{t("siteWork.systemWork")}</option>
              <option value="exception">{t("siteWork.exception")}</option>
              <option value="additional_work">{t("siteWork.additionalWork")}</option>
            </select>
          </label>
          <label className="block text-sm text-gray-700">
            {t("siteWork.source")}
            <select
              value={manualSource}
              onChange={(event) => setManualSource(event.target.value as SiteWorkItem["source"])}
              className="mt-1 block border border-gray-300 rounded-md px-3 py-2 bg-white"
            >
              <option value="site_report">{t("siteWork.siteReport")}</option>
              <option value="whatsapp">{t("siteWork.whatsapp")}</option>
            </select>
          </label>
          <label className="block text-sm text-gray-700">
            {t("siteWork.date")}
            <input
              type="date"
              value={manualDate}
              onChange={(event) => setManualDate(event.target.value)}
              className="mt-1 block border border-gray-300 rounded-md px-3 py-2"
            />
          </label>
        </div>
        <button
          type="button"
          onClick={onAdd}
          disabled={adding || manualDescription.trim().length < 3}
          className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm disabled:opacity-50"
        >
          {adding ? t("siteWork.processing") : t("siteWork.add")}
        </button>
      </div>

      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex flex-wrap gap-4">
          <label className="block text-sm text-gray-700">
            {t("siteWork.system")}
            <select
              value={filterSystem}
              onChange={(event) => setFilterSystem(event.target.value)}
              className="mt-1 block border border-gray-300 rounded-md px-3 py-2 bg-white"
            >
              <option value="">{t("siteWork.all")}</option>
              {systemFilterOptions.map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
            </select>
          </label>
          <label className="block text-sm text-gray-700">
            {t("siteWork.classification")}
            <select
              value={filterClassification}
              onChange={(event) => setFilterClassification(event.target.value)}
              className="mt-1 block border border-gray-300 rounded-md px-3 py-2 bg-white"
            >
              <option value="">{t("siteWork.all")}</option>
              <option value="system">{t("siteWork.systemWork")}</option>
              <option value="exception">{t("siteWork.exception")}</option>
              <option value="additional_work">{t("siteWork.additionalWork")}</option>
            </select>
          </label>
          <label className="block text-sm text-gray-700">
            {t("siteWork.source")}
            <select
              value={filterSource}
              onChange={(event) => setFilterSource(event.target.value)}
              className="mt-1 block border border-gray-300 rounded-md px-3 py-2 bg-white"
            >
              <option value="">{t("siteWork.all")}</option>
              <option value="site_report">{t("siteWork.siteReport")}</option>
              <option value="whatsapp">{t("siteWork.whatsapp")}</option>
            </select>
          </label>
          <label className="block text-sm text-gray-700">
            {t("siteWork.date")}
            <input
              type="date"
              value={filterDate}
              onChange={(event) => setFilterDate(event.target.value)}
              className="mt-1 block border border-gray-300 rounded-md px-3 py-2"
            />
          </label>
        </div>
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
              <th className="px-3 py-2 text-start">{t("siteWork.notes")}</th>
              <th className="px-3 py-2 text-start">{t("siteWork.photosCol")}</th>
              <th className="px-3 py-2" />
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={8} className="px-3 py-6 text-center text-gray-500">
                  {t("projects.loading")}
                </td>
              </tr>
            ) : visibleItems.length === 0 ? (
              <tr>
                <td colSpan={8} className="px-3 py-6 text-center text-gray-500">
                  {items.length === 0 ? t("siteWork.empty") : t("siteWork.noMatches")}
                </td>
              </tr>
            ) : (
              visibleItems.map((item) => {
                const isException =
                  item.classification === "exception" ||
                  (item.system_name || "").trim().toLowerCase() === "exception";
                return (
                <tr
                  key={item.id}
                  className={
                    isException
                      ? "border-t border-red-200 bg-red-50 text-red-900"
                      : "border-t border-gray-100"
                  }
                >
                  <td className="px-3 py-2">{item.description}</td>
                  <td className="px-3 py-2">
                    <select
                      aria-label={t("siteWork.changeSystem")}
                      value={item.system_name || ""}
                      onChange={(event) => onSystemChange(item, event.target.value)}
                      className="border border-gray-300 rounded-md px-2 py-1 bg-white text-gray-900"
                    >
                      {item.system_name &&
                        !systems.some(
                          (name) => name.toLowerCase() === item.system_name?.toLowerCase()
                        ) && <option value={item.system_name}>{item.system_name}</option>}
                      {systems.map((name) => (
                        <option key={name} value={name}>
                          {name}
                        </option>
                      ))}
                    </select>
                    {item.system_name && (
                      <Link
                        to={`/calculation-sheets?system=${encodeURIComponent(item.system_name)}`}
                        className="mt-1 block text-xs text-blue-700 underline"
                      >
                        {t("siteWork.openSheets")}
                      </Link>
                    )}
                  </td>
                  <td className="px-3 py-2">{classificationLabel(item.classification)}</td>
                  <td className="px-3 py-2">{sourceLabel(item.source)}</td>
                  <td className="px-3 py-2">{item.work_date || "—"}</td>
                  <td className="px-3 py-2">
                    <textarea
                      aria-label={t("siteWork.notes")}
                      value={noteDrafts[item.id] ?? item.notes ?? ""}
                      onChange={(event) =>
                        setNoteDrafts((current) => ({
                          ...current,
                          [item.id]: event.target.value,
                        }))
                      }
                      onBlur={() => void onNotesBlur(item)}
                      rows={2}
                      className="w-52 border border-gray-300 rounded-md px-2 py-1 bg-white text-gray-900"
                    />
                  </td>
                  <td className="px-3 py-2">
                    <div className="flex gap-2">
                      {(item.photo_paths || []).map((path) =>
                        path.toLowerCase().endsWith(".pdf") ? (
                          <button
                            key={path}
                            type="button"
                            onClick={() => void onOpenAttachment(item.id, path)}
                            className="inline-flex items-center gap-1 rounded border border-gray-400 bg-white px-1.5 py-0.5 text-blue-700"
                            title={path}
                          >
                            <FileText className="h-4 w-4" />
                            PDF
                          </button>
                        ) : (
                          <a key={path} href={path} target="_blank" rel="noreferrer">
                            <img src={path} alt="" className="h-10 w-10 object-cover rounded" />
                          </a>
                        )
                      )}
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
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default SiteReports;
