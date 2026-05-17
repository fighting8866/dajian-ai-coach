import { getAuthToken, clearAuthSession } from '../utils/authSession';

// API 基地址配置
const apiBase = import.meta.env.VITE_API_BASE || '/api';

function withAuthHeaders(base = {}) {
  const h = { ...base };
  const t = getAuthToken();
  if (t) h.Authorization = `Bearer ${t}`;
  return h;
}

function redirectToLoginAfterUnauthorized() {
  try {
    clearAuthSession();
    const redir = `${window.location.pathname}${window.location.search || ''}` || '/home';
    window.location.assign(`/login?redirect=${encodeURIComponent(redir)}`);
  } catch {
    try {
      window.location.assign('/login');
    } catch (_) {}
  }
}

/**
 * 统一拼接 API URL：
 * 1) 去掉重复 /api 前缀（避免 /api/api/...）
 * 2) 规整双斜杠
 */
const buildApiUrl = (endpoint) => {
  let base = String(apiBase || '/api').replace(/\/+$/, '');
  // 绝对地址仅写到 host:port 时，后端实际挂载在 /api 下，补上 /api（避免 /qa/followup 404）
  if (/^https?:\/\/[^/]+$/i.test(base)) {
    base = `${base}/api`;
  }
  const epRaw = String(endpoint || '');
  const ep = epRaw.startsWith('/') ? epRaw : `/${epRaw}`;

  // 如果 base 已经以 /api 结尾，endpoint 再以 /api 开头则去重
  const normalizedEndpoint =
    /\/api$/i.test(base) && /^\/api(\/|$)/i.test(ep)
      ? ep.replace(/^\/api/i, '')
      : ep;

  return `${base}${normalizedEndpoint}`.replace(/([^:]\/)\/+/g, '$1');
};

/**
 * 通用 GET 请求
 * @param {string} endpoint - API 端点
 * @returns {Promise<any>} 响应数据
 */
export const getJson = async (endpoint) => {
  const url = buildApiUrl(endpoint);
  const response = await fetch(url, {
    method: 'GET',
    headers: withAuthHeaders({
      'Content-Type': 'application/json',
    }),
  });

  if (response.status === 401) {
    redirectToLoginAfterUnauthorized();
    const text = await response.text();
    throw new Error(`HTTP error! status: 401; body: ${text}`);
  }

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`HTTP error! status: ${response.status}; body: ${text}`);
  }
  
  return await response.json();
};

/**
 * PUT JSON
 * @param {string} endpoint
 * @param {object} data
 */
export const putJson = async (endpoint, data) => {
  const url = buildApiUrl(endpoint);
  const response = await fetch(url, {
    method: 'PUT',
    headers: withAuthHeaders({
      'Content-Type': 'application/json',
      Accept: 'application/json',
    }),
    body: JSON.stringify(data ?? {}),
  });

  if (response.status === 401) {
    redirectToLoginAfterUnauthorized();
    const text = await response.text();
    throw new Error(`HTTP error! status: 401; body: ${text}`);
  }

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`HTTP error! status: ${response.status}; body: ${text}`);
  }

  return await response.json();
};

/**
 * 通用 POST 请求
 * @param {string} endpoint - API 端点
 * @param {object} data - 请求数据
 * @returns {Promise<any>} 响应数据
 */
export const postJson = async (endpoint, data) => {
  const url = buildApiUrl(endpoint);
  const isFollowup = /\/qa\/followup$/i.test(url) || String(endpoint || '').includes('followup');
  if (isFollowup) {
    console.log('[api.postJson] /qa/followup final url =', url, 'method=POST Content-Type=application/json');
  }
  const response = await fetch(url, {
    method: 'POST',
    headers: withAuthHeaders({
      'Content-Type': 'application/json',
      Accept: 'application/json',
    }),
    body: JSON.stringify(data ?? {}),
  });

  if (response.status === 401) {
    redirectToLoginAfterUnauthorized();
    const text = await response.text();
    throw new Error(`HTTP error! status: 401; body: ${text}`);
  }

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`HTTP error! status: ${response.status}; body: ${text}`);
  }
  
  return await response.json();
};

/**
 * DELETE JSON
 * @param {string} endpoint
 */
export const deleteJson = async (endpoint) => {
  const url = buildApiUrl(endpoint);
  const response = await fetch(url, {
    method: 'DELETE',
    headers: withAuthHeaders({
      Accept: 'application/json',
    }),
  });

  if (response.status === 401) {
    redirectToLoginAfterUnauthorized();
    const text = await response.text();
    throw new Error(`HTTP error! status: 401; body: ${text}`);
  }

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`HTTP error! status: ${response.status}; body: ${text}`);
  }

  return await response.json();
};

/**
 * 文件上传
 * @param {string} endpoint - API 端点
 * @param {FormData|File} data - FormData 对象或 File 对象
 * @returns {Promise<any>} 响应数据
 */
export const uploadFile = async (endpoint, data) => {
  const url = buildApiUrl(endpoint);
  console.log('[uploadFile] apiBase =', apiBase);
  console.log('[uploadFile] endpoint =', endpoint);
  console.log('[uploadFile] final url =', url);
  let body;
  
  // 如果是 File 对象，创建 FormData
  if (data instanceof File) {
    const formData = new FormData();
    formData.append('file', data);
    body = formData;
  } else {
    // 否则直接使用传入的 FormData
    body = data;
  }
  
  const response = await fetch(url, {
    method: 'POST',
    headers: withAuthHeaders({}),
    body: body,
  });

  if (response.status === 401) {
    redirectToLoginAfterUnauthorized();
    const text = await response.text();
    throw new Error(`HTTP error! status: 401; body: ${text}`);
  }

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`HTTP error! status: ${response.status}; body: ${text}`);
  }
  
  return await response.json();
};