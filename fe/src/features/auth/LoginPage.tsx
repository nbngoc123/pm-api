import { Clock, ListChecks, Target, type LucideIcon } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { errorMessage } from '@/api/client'
import { useAuth } from '@/auth/useAuth'
import { Button } from '@/components/ui/button'
import { Field, Input } from '@/components/ui/form'

const HIGHLIGHTS: { icon: LucideIcon; title: string; text: string }[] = [
  { icon: ListChecks, title: 'Giao việc và theo dõi', text: 'Bảng Kanban, phân công và xét duyệt cho từng dự án.' },
  { icon: Clock, title: 'Chấm công theo công việc', text: 'Ghi giờ làm thực tế, so với ngân sách giờ của dự án.' },
  { icon: Target, title: 'Chấm KPI minh bạch', text: 'Điểm KPI tính từ tiến độ, giờ làm và vi phạm.' },
]

export function LoginPage() {
  const { user, login } = useAuth()
  const location = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  if (user) return <Navigate to={(location.state as { from?: string } | null)?.from ?? '/'} replace />

  async function submit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await login(email, password)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="flex min-h-full">
      <aside className="hidden w-[42%] max-w-xl flex-col justify-between bg-rail p-10 text-rail-fg lg:flex">
        <div className="flex items-center gap-2 text-white">
          <span className="flex size-7 items-center justify-center rounded-md bg-primary text-sm font-bold">P</span>
          <span className="text-base font-semibold">PM-KPI</span>
        </div>
        <div>
          <h2 className="text-2xl leading-tight font-semibold text-white">Quản lý dự án và KPI trên một nơi</h2>
          <ul className="mt-8 flex flex-col gap-5">
            {HIGHLIGHTS.map((h) => (
              <li key={h.title} className="flex gap-3">
                <span className="flex size-8 shrink-0 items-center justify-center rounded-md bg-rail-active text-white">
                  <h.icon className="size-4" />
                </span>
                <span>
                  <span className="block text-sm font-medium text-white">{h.title}</span>
                  <span className="block text-sm">{h.text}</span>
                </span>
              </li>
            ))}
          </ul>
        </div>
        <p className="text-xs">Hệ thống nội bộ. Chỉ dành cho nhân viên công ty.</p>
      </aside>

      <main className="flex flex-1 items-center justify-center bg-surface p-6">
        <form onSubmit={submit} className="flex w-full max-w-sm flex-col gap-4">
          <div>
            <span className="mb-4 flex size-9 items-center justify-center rounded-md bg-primary text-base font-bold text-white lg:hidden">P</span>
            <h1 className="text-xl font-semibold">Đăng nhập</h1>
            <p className="text-sm text-muted">Dùng email công ty và mật khẩu được cấp.</p>
          </div>
          <Field label="Email">
            <Input type="email" autoComplete="username" placeholder="ten@congty.vn" value={email} onChange={(e) => setEmail(e.target.value)} required autoFocus className="h-9" />
          </Field>
          <Field label="Mật khẩu">
            <Input type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required className="h-9" />
          </Field>
          {error ? (
            <p role="alert" className="rounded-md bg-danger-soft px-3 py-2 text-sm text-danger-soft-fg">
              {error}
            </p>
          ) : null}
          <Button type="submit" variant="primary" loading={submitting} className="h-9">
            {submitting ? 'Đang đăng nhập…' : 'Đăng nhập'}
          </Button>
          <p className="border-t pt-4 text-sm text-muted">Chưa có tài khoản hoặc quên mật khẩu? Liên hệ quản trị viên hệ thống để được cấp.</p>
        </form>
      </main>
    </div>
  )
}
