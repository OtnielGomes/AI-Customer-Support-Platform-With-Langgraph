export async function clientFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/support${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(body || `Request failed (${response.status})`);
  }
  return (await response.json()) as T;
}

export const clientFetcher = <T>(path: string): Promise<T> => clientFetch<T>(path);
