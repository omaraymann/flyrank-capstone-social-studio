const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export async function api(path, { token, method = "GET", body } = {}) {
  const response = await fetch(`${API_URL}${path}`, {
    method,
    headers: {
      ...(body ? { "Content-Type": "application/json" } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const payload = await response.json();
      message = Array.isArray(payload.detail)
        ? payload.detail.map((item) => item.msg).join(", ")
        : payload.detail || message;
    } catch {
      // Keep the safe status message when the response is not JSON.
    }
    throw new Error(message);
  }
  return response.status === 204 ? null : response.json();
}
