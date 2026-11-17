import { createContext, useContext } from 'react'
import type { Me } from '@/api/types'

export interface AuthContextValue {
  user: Me | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  /** Quyền cấp hệ thống. Quyền trong dự án lấy từ useProjectAccess. */
  can: (permission: string) => boolean
}

export const AuthContext = createContext<AuthContextValue | null>(null)

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth phải được gọi bên trong AuthProvider')
  return ctx
}
