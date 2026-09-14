import React, { useCallback, useEffect, useMemo, useState } from "react";
import { getProjectItem, setProjectItem } from "../utils/localStorage";

const STORAGE_PREFIX = "table-column-widths:";

function loadWidths(
  storageKey: string,
  defaults: Record<string, number>
): Record<string, number> {
  const saved = getProjectItem(`${STORAGE_PREFIX}${storageKey}`);
  if (!saved) return { ...defaults };
  try {
    const parsed = JSON.parse(saved) as Record<string, unknown>;
    const next = { ...defaults };
    for (const [key, value] of Object.entries(parsed)) {
      if (typeof value === "number" && Number.isFinite(value) && value > 0) {
        next[key] = value;
      }
    }
    return next;
  } catch {
    return { ...defaults };
  }
}

export function useResizableColumns(
  storageKey: string,
  defaults: Record<string, number>,
  options?: { minWidth?: number; maxWidth?: number }
) {
  const minWidth = options?.minWidth ?? 56;
  const maxWidth = options?.maxWidth ?? 720;
  const [widths, setWidths] = useState(() => loadWidths(storageKey, defaults));

  useEffect(() => {
    setProjectItem(`${STORAGE_PREFIX}${storageKey}`, JSON.stringify(widths));
  }, [storageKey, widths]);

  const startResize = useCallback(
    (columnKey: string, startX: number) => {
      const startWidth = widths[columnKey] ?? defaults[columnKey] ?? 120;
      const handleMove = (event: PointerEvent) => {
        const delta = event.clientX - startX;
        const next = Math.min(
          maxWidth,
          Math.max(minWidth, startWidth + delta)
        );
        setWidths((prev) => ({ ...prev, [columnKey]: next }));
      };
      const handleUp = () => {
        window.removeEventListener("pointermove", handleMove);
        window.removeEventListener("pointerup", handleUp);
        document.body.style.cursor = "";
        document.body.style.userSelect = "";
      };
      document.body.style.cursor = "col-resize";
      document.body.style.userSelect = "none";
      window.addEventListener("pointermove", handleMove);
      window.addEventListener("pointerup", handleUp);
    },
    [defaults, maxWidth, minWidth, widths]
  );

  const colStyle = useCallback(
    (columnKey: string): React.CSSProperties => {
      const width = widths[columnKey] ?? defaults[columnKey];
      if (!width) return {};
      return { width, minWidth: width, maxWidth: width };
    },
    [defaults, widths]
  );

  const tableWidth = useMemo(
    () =>
      Object.keys(defaults).reduce(
        (sum, key) => sum + (widths[key] ?? defaults[key] ?? 0),
        0
      ),
    [defaults, widths]
  );

  return { widths, startResize, colStyle, tableWidth };
}

export function startHeaderColumnResize(
  event: React.PointerEvent,
  startResize: (columnKey: string, startX: number) => void,
  isRTL = false
) {
  const th = (event.target as HTMLElement).closest(
    "th[data-col-key]"
  ) as HTMLTableCellElement | null;
  if (!th) return;
  const key = th.dataset.colKey;
  if (!key) return;
  const rect = th.getBoundingClientRect();
  const dist = isRTL ? event.clientX - rect.left : rect.right - event.clientX;
  if (dist > 10) return;
  event.preventDefault();
  startResize(key, event.clientX);
}
