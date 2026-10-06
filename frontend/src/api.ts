const TOKEN_KEY = "impulso_token";

export const tokenStore = {
  get: () => sessionStorage.getItem(TOKEN_KEY),
  set: (t: string) => sessionStorage.setItem(TOKEN_KEY, t),
  clear: () => sessionStorage.removeItem(TOKEN_KEY),
};

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

function errorMessage(body: unknown): string {
  const detail = (body as { detail?: unknown })?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d: { msg?: string }) => (d.msg ?? "").replace(/^Value error, /, ""))
      .join(". ");
  }
  return "Ocurrió un error inesperado";
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  const token = tokenStore.get();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (options.body && !(options.body instanceof URLSearchParams)) {
    headers.set("Content-Type", "application/json");
  }

  const res = await fetch(path, { ...options, headers });
  if (res.status === 401 && token) {
    tokenStore.clear();
    window.location.href = "/crm/login";
  }
  const body = res.headers.get("content-type")?.includes("json") ? await res.json() : null;
  if (!res.ok) throw new ApiError(res.status, errorMessage(body));
  return body as T;
}

export const login = (email: string, password: string) =>
  api<{ access_token: string }>("/api/auth/login", {
    method: "POST",
    body: new URLSearchParams({ username: email, password }),
  });

export async function downloadFile(path: string, filename: string) {
  const res = await fetch(path, { headers: { Authorization: `Bearer ${tokenStore.get()}` } });
  if (!res.ok) throw new ApiError(res.status, "No se pudo descargar el archivo");
  const url = URL.createObjectURL(await res.blob());
  const a = Object.assign(document.createElement("a"), { href: url, download: filename });
  a.click();
  URL.revokeObjectURL(url);
}
