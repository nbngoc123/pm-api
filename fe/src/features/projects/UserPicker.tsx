import { useState } from 'react'
import type { UserLookup } from '@/api/types'
import { Input } from '@/components/ui/form'
import { useUserLookup } from './queries'

/** Ô tìm người dùng theo tên hoặc email (backend yêu cầu ít nhất 2 ký tự). */
export function UserPicker({ value, onChange }: { value: UserLookup | null; onChange: (user: UserLookup | null) => void }) {
  const [q, setQ] = useState('')
  const results = useUserLookup(q)

  if (value) {
    return (
      <div className="flex h-8 items-center justify-between rounded-md border border-border-strong px-2.5 text-sm">
        <span className="truncate">
          {value.ho_ten} <span className="text-muted">({value.email})</span>
        </span>
        <button type="button" className="text-xs text-primary hover:underline" onClick={() => onChange(null)}>
          Đổi
        </button>
      </div>
    )
  }
  return (
    <div>
      <Input placeholder="Nhập tên hoặc email" value={q} onChange={(e) => setQ(e.target.value)} />
      {q.trim().length >= 2 ? (
        <ul className="mt-1 max-h-40 overflow-y-auto rounded-md border">
          {results.data?.length === 0 ? <li className="px-2.5 py-1.5 text-sm text-muted">Không tìm thấy ai.</li> : null}
          {results.data?.map((u) => (
            <li key={u.ma_nd}>
              <button type="button" className="w-full px-2.5 py-1.5 text-left text-sm hover:bg-surface-2" onClick={() => onChange(u)}>
                {u.ho_ten} <span className="text-muted">({u.email})</span>
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  )
}
