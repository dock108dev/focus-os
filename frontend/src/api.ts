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
    const detail = typeof payload?.detail === "string" ? payload.detail : fallback;
    return `${fallback} (${response.status}): ${detail}`;
  } catch {
    return `${fallback} (${response.status})`;
  }
}

export async function requestJson<T>(url: string, init: RequestInit | undefined, fallback: string): Promise<T> {
  const response = await fetch(url, init);
  if (!response.ok) throw new Error(await readApiError(response, fallback));
  return response.json() as Promise<T>;
}
