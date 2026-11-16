import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useCallback, useEffect, useMemo, type ReactNode } from 'react'
import { api, setSessionExpiredHandler, tokens } from '@/api/client'
import type { Me, TokenOut } from '@/api/types'
import { AuthContext, type AuthContextValue } from './useAuth'

export function AuthProvider({ children }: { children: ReactNode }) {
  const qc = useQueryClient()
  const me = useQuery({
    queryKey: ['me'],
    queryFn: () => api.get<Me>('/auth/me'),
    enabled: !!tokens.access,
    retry: false,
    staleTime: 5 * 60_000,
  })

  const logout = useCallback(() => {
    tokens.clear()
    qc.clear()
    qc.setQueryData(['me'], null)
  }, [qc])

  useEffect(() => setSessionExpiredHandler(() => qc.setQueryData(['me'], null)), [qc])

  const login = useCallback(
    async (email: string, password: string) => {
      const t = await api.post<TokenOut>('/auth/login', { email, password })
      tokens.set(t)
      await qc.fetchQuery({ queryKey: ['me'], queryFn: () => api.get<Me>('/auth/me') })
    },
    [qc],
  )

  const value = useMemo<AuthContextValue>(() => {
    const user = me.data ?? null
    return {
      user,
      loading: !!tokens.access && me.isPending,
      login,
      logout,
      can: (p) => !!user?.permissions.includes(p),
    }
  }, [me.data, me.isPending, login, logout])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
