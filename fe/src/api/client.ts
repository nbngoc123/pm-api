import type { TokenOut } from './types'

const BASE = '/api/v1'
const ACCESS_KEY = 'pmkpi.access'
const REFRESH_KEY = 'pmkpi.refresh'

export interface FieldError {
  field: string
  message: string
}

/** Lỗi theo định dạng thống nhất của backend: {error: {code, message, details}}. */
export class ApiError extends Error {
  status: number
  code: string
  details: FieldError[] | null

  constructor(status: number, code: string, message: string, details: FieldError[] | null = null) {
    super(message)
    this.status = status
    this.code = code
    this.details = details
  }
}

export const tokens = {
  get access() {
    return localStorage.getItem(ACCESS_KEY)
  },
  get refresh() {
    return localStorage.getItem(REFRESH_KEY)
  },
  set(t: Pick<TokenOut, 'access_token' | 'refresh_token'>) {
    localStorage.setItem(ACCESS_KEY, t.access_token)
    localStorage.setItem(REFRESH_KEY, t.refresh_token)
  },
  clear() {
    localStorage.removeItem(ACCESS_KEY)
    localStorage.removeItem(REFRESH_KEY)
  },
}

let onSessionExpired: () => void = () => {}
export function setSessionExpiredHandler(fn: () => void) {
  onSessionExpired = fn
}

type Query = Record<string, string | number | boolean | null | undefined>

interface RequestOptions {
  query?: Query
  body?: unknown
  form?: FormData
  raw?: boolean
}

function buildUrl(path: string, query?: Query) {
  const qs = new URLSearchParams()
  for (const [k, v] of Object.entries(query ?? {})) {
    if (v !== undefined && v !== null && v !== '') qs.set(k, String(v))
  }
  const s = qs.toString()
  return BASE + path + (s ? `?${s}` : '')
}

async function toApiError(res: Response): Promise<ApiError> {
  try {
    const { error } = await res.json()
    return new ApiError(res.status, error.code, error.message, error.details ?? null)
  } catch {
    return new ApiError(res.status, 'UNKNOWN', 'Máy chủ không phản hồi đúng định dạng. Thử lại sau.')
  }
}

function send(method: string, path: string, opts: RequestOptions) {
  const headers: Record<string, string> = {}
  if (tokens.access) headers.Authorization = `Bearer ${tokens.access}`
  if (opts.body !== undefined) headers['Content-Type'] = 'application/json'
  return fetch(buildUrl(path, opts.query), {
    method,
    headers,
    body: opts.form ?? (opts.body !== undefined ? JSON.stringify(opts.body) : undefined),
  })
}

let refreshing: Promise<boolean> | null = null

/** Chỉ một lượt refresh chạy tại một thời điểm, các request khác chờ chung kết quả. */
function refreshSession(): Promise<boolean> {
  refreshing ??= (async () => {
    const refresh_token = tokens.refresh
    if (!refresh_token) return false
    const res = await fetch(`${BASE}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token }),
    })
    if (!res.ok) return false
    tokens.set(await res.json())
    return true
  })().finally(() => {
    refreshing = null
  })
  return refreshing
}

async function request<T>(method: string, path: string, opts: RequestOptions = {}): Promise<T> {
  let res: Response
  try {
    res = await send(method, path, opts)
    if (res.status === 401 && tokens.access && !path.startsWith('/auth/login')) {
      const err = await toApiError(res.clone())
      if (err.code === 'TOKEN_INVALID' && (await refreshSession())) {
        res = await send(method, path, opts)
      } else if (err.code !== 'BAD_CREDENTIALS') {
        tokens.clear()
        onSessionExpired()
        throw err
      }
    }
  } catch (e) {
    if (e instanceof ApiError) throw e
    throw new ApiError(0, 'NETWORK', 'Không kết nối được máy chủ. Kiểm tra mạng rồi thử lại.')
  }
  if (!res.ok) throw await toApiError(res)
  if (opts.raw) return res as T
  return res.status === 204 ? (undefined as T) : res.json()
}

export const api = {
  get: <T>(path: string, query?: Query) => request<T>('GET', path, { query }),
  post: <T>(path: string, body?: unknown) => request<T>('POST', path, { body: body ?? {} }),
  put: <T>(path: string, body: unknown) => request<T>('PUT', path, { body }),
  patch: <T>(path: string, body: unknown) => request<T>('PATCH', path, { body }),
  delete: <T>(path: string) => request<T>('DELETE', path),
  upload: <T>(path: string, form: FormData) => request<T>('POST', path, { form }),
  /** Tải tệp cần header Authorization nên phải lấy blob rồi tự tạo link. */
  async download(path: string, filename: string) {
    const res = await request<Response>('GET', path, { raw: true })
    const url = URL.createObjectURL(await res.blob())
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
  },
}

export function errorMessage(e: unknown) {
  return e instanceof Error ? e.message : 'Đã có lỗi xảy ra.'
}
