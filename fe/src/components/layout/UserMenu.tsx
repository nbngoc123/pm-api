import { KeyRound, LogOut, Moon, Sun } from 'lucide-react'
import { DropdownMenu } from 'radix-ui'
import { useEffect, useState } from 'react'
import { useAuth } from '@/auth/useAuth'
import { Avatar } from '@/components/ui/misc'
import { ChangePasswordDialog } from '@/features/auth/ChangePasswordDialog'
import { SYSTEM_ROLE } from '@/lib/labels'
import { useLocalState } from '@/lib/useLocalState'

const itemClass = 'flex cursor-pointer items-center gap-2 rounded px-2 py-1.5 text-sm outline-none data-highlighted:bg-surface-2'

export function UserMenu({ expanded }: { expanded: boolean }) {
  const { user, logout } = useAuth()
  const [dark, setDark] = useLocalState<boolean>('pmkpi.dark', false)
  const [changingPassword, setChangingPassword] = useState(false)

  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark)
  }, [dark])

  if (!user) return null
  return (
    <>
      <DropdownMenu.Root>
        <DropdownMenu.Trigger className="flex h-8 items-center gap-2 rounded-md px-1 hover:bg-rail-active hover:text-white" aria-label="Tài khoản">
          <Avatar name={user.ho_ten} />
          {expanded ? <span className="truncate text-sm">{user.ho_ten}</span> : null}
        </DropdownMenu.Trigger>
        <DropdownMenu.Portal>
          <DropdownMenu.Content side="right" align="end" sideOffset={8} className="z-50 w-56 rounded-lg border bg-surface p-1 text-fg shadow-xl">
            <div className="border-b px-2 py-1.5">
              <p className="truncate text-sm font-medium">{user.ho_ten}</p>
              <p className="truncate text-xs text-muted">{user.email}</p>
              <p className="text-xs text-subtle">{SYSTEM_ROLE[user.vai_tro] ?? user.vai_tro}</p>
            </div>
            <DropdownMenu.Item className={itemClass} onSelect={() => setDark(!dark)}>
              {dark ? <Sun className="size-4" /> : <Moon className="size-4" />}
              {dark ? 'Giao diện sáng' : 'Giao diện tối'}
            </DropdownMenu.Item>
            <DropdownMenu.Item className={itemClass} onSelect={() => setChangingPassword(true)}>
              <KeyRound className="size-4" />
              Đổi mật khẩu
            </DropdownMenu.Item>
            <DropdownMenu.Item className={itemClass} onSelect={logout}>
              <LogOut className="size-4" />
              Đăng xuất
            </DropdownMenu.Item>
          </DropdownMenu.Content>
        </DropdownMenu.Portal>
      </DropdownMenu.Root>
      <ChangePasswordDialog open={changingPassword} onOpenChange={setChangingPassword} />
    </>
  )
}
