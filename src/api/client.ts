export function apiUrl(path: string, query: Record<string, string | number | boolean | undefined> = {}) {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined) params.set(key, String(value));
  }
  const encoded = params.toString();
  return encoded ? `${path}?${encoded}` : path;
}

export async function postJson<T>(path: string, query: Record<string, string | number | boolean | undefined> = {}, body?: unknown): Promise<T> {
  const response = await fetch(apiUrl(path, query), {
    method: "POST",
    ...(body === undefined ? {} : {
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    })
  });
  if (!response.ok) throw new Error(await response.text());
  return response.json() as Promise<T>;
}
