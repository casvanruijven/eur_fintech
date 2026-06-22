// Export downloads via fetch + blob (not a bare <a download>), so:
//  - the server-provided filename (Content-Disposition) is respected,
//  - the cookie is sent (credentials: include),
//  - HTTP errors (401 "log in to export", 422 "missing VAT") surface as messages
//    instead of silently navigating to an error page.

function filenameFromDisposition(header: string | null): string | null {
  if (!header) return null;
  const match = /filename="?([^"]+)"?/.exec(header);
  return match ? match[1] : null;
}

export async function downloadFile(url: string, fallbackName = "download"): Promise<void> {
  const res = await fetch(url, { credentials: "include" });
  if (!res.ok) {
    let message = `Download failed (${res.status})`;
    if (res.status === 401) {
      message = "Please log in to export the structured e-invoice.";
    } else {
      try {
        const body = await res.json();
        if (typeof body?.detail === "string") message = body.detail;
      } catch {
        /* keep the generic message */
      }
    }
    throw new Error(message);
  }

  const blob = await res.blob();
  const name = filenameFromDisposition(res.headers.get("content-disposition")) ?? fallbackName;
  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = name;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(objectUrl);
}
