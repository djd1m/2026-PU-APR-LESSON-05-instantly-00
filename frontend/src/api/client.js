const BASE_URL = '/api';

async function request(url, options = {}) {
  const token = localStorage.getItem('token');
  const headers = { ...options.headers };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${BASE_URL}${url}`, { ...options, headers });

  if (response.status === 401) {
    localStorage.removeItem('token');
    window.location.href = '/login';
    throw { detail: 'Unauthorized' };
  }

  if (!response.ok) {
    let body;
    try {
      body = await response.json();
    } catch {
      body = { detail: response.statusText };
    }
    throw { detail: body.detail || body.message || response.statusText };
  }

  return response.json();
}

export const api = {
  get(url) {
    return request(url);
  },

  post(url, data) {
    return request(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
  },

  put(url, data) {
    return request(url, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
  },

  patch(url, data) {
    return request(url, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
  },

  del(url) {
    return request(url, { method: 'DELETE' });
  },

  postForm(url, data) {
    return request(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: data.toString(),
    });
  },
};
