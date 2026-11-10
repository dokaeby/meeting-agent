let csrf = '';

export function setCsrf(value) {
  csrf = value;
}

export async function request(path, options = {}) {
  const headers = new Headers(options.headers);
  if (!(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }
  if (csrf) {
    headers.set('X-CSRF-Token', csrf);
  }
  const response = await fetch('/api/v1' + path, {
    ...options,
    headers,
    credentials: 'same-origin',
  });
  if (!response.ok) {
    const error = await response
      .json()
      .catch(() => ({ message: '요청을 완료하지 못했습니다' }));
    throw new Error(error.message || '요청을 완료하지 못했습니다');
  }
  return response.json();
}

export const json = (method, body) => ({
  method,
  body: JSON.stringify(body),
});

