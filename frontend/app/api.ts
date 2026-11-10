export async function api<T>(
  path: string,
  body?: unknown,
  role?: string,
  method?: string,
): Promise<T> {
  const res = await fetch("/api" + path, {
    method: method || (body ? "POST" : "GET"),
    headers:
      body instanceof FormData
        ? {}
        : {
            "Content-Type": "application/json",
            ...(role ? { "X-Demo-Role": role } : {}),
          },
    body:
      body instanceof FormData ? body : body ? JSON.stringify(body) : undefined,
    cache: "no-store",
  });
  if (!res.ok) {
    let message = `Request failed (${res.status})`;
    try {
      const b = await res.json();
      message =
        typeof b.detail === "string" ? b.detail : JSON.stringify(b.detail);
    } catch {}
    throw new Error(message);
  }
  return res.json();
}

export function uploadAudio<T>(
  body: FormData,
  onProgress: (percent: number) => void,
): Promise<T> {
  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest();
    request.open("POST", "/api/conversations/upload");
    request.upload.onprogress = (event) => {
      if (event.lengthComputable)
        onProgress(Math.round((event.loaded / event.total) * 100));
    };
    request.onerror = () =>
      reject(
        new Error("Audio upload failed. Check your connection and retry."),
      );
    request.onload = () => {
      try {
        const result = JSON.parse(request.responseText);
        if (request.status >= 200 && request.status < 300) resolve(result as T);
        else
          reject(
            new Error(
              typeof result.detail === "string"
                ? result.detail
                : `Upload failed (${request.status})`,
            ),
          );
      } catch {
        reject(new Error("The server returned an invalid upload response."));
      }
    };
    request.send(body);
  });
}
