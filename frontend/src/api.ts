export function sourceFromFile(file: File) {
  const name = file.name.toLowerCase();
  if (name.includes("fidelity")) return "Fidelity";
  if (name.includes("sofi")) return "SoFi";
  if (name.includes("tasty")) return "Tastytrade";
  return "Manual";
}

async function readApiError(response: Response, fallback: string): Promise<string> {
  try {
    const payload = await response.json();
    const detail = apiErrorDetail(payload, fallback);
    return `${fallback} (${response.status}): ${detail}`;
  } catch {
    return `${fallback} (${response.status})`;
  }
}

function apiErrorDetail(payload: unknown, fallback: string): string {
  if (!payload || typeof payload !== "object" || !("detail" in payload)) {
    return fallback;
  }
  const detail = payload.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => {
        if (!item || typeof item !== "object") return "";
        const message = "msg" in item && typeof item.msg === "string" ? item.msg : "";
        const location =
          "loc" in item && Array.isArray(item.loc) ? item.loc.join(".") : "";
        return [location, message].filter(Boolean).join(": ");
      })
      .filter(Boolean);
    return messages.length ? messages.slice(0, 3).join("; ") : fallback;
  }
  return fallback;
}

export async function requestJson<T>(url: string, init: RequestInit | undefined, fallback: string): Promise<T> {
  const response = await fetch(url, init);
  if (!response.ok) throw new Error(await readApiError(response, fallback));
  return response.json() as Promise<T>;
}
