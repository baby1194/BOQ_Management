/** Trigger a file save to the browser's default download folder. */
export function triggerBrowserDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  // Revoke after the browser has started the download. Immediate revoke
  // causes Chrome to fail with "Couldn't download — site wasn't available".
  window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
}

export function filenameFromExportPath(exportPath: string): string {
  return exportPath.split("/").pop() || "export";
}
