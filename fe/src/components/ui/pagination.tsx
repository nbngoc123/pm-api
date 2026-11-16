import { ChevronLeft, ChevronRight } from 'lucide-react'
import { Button } from './button'
import { Select } from './form'

const PAGE_SIZES = [10, 20, 50, 100]

interface PaginationProps {
  page: number
  size: number
  total: number
  onPageChange: (page: number) => void
  onSizeChange?: (size: number) => void
}

/** Thanh phân trang ở chân bảng. Trang bắt đầu từ 1, khớp với query page và size của backend. */
export function Pagination({ page, size, total, onPageChange, onSizeChange }: PaginationProps) {
  const pages = Math.max(1, Math.ceil(total / size))
  const from = total === 0 ? 0 : (page - 1) * size + 1
  const to = Math.min(total, page * size)
  return (
    <div className="flex flex-wrap items-center justify-between gap-2 px-4 py-2 text-sm text-muted">
      <span className="tabular-nums">{total === 0 ? 'Không có bản ghi' : `${from}–${to} trên ${total}`}</span>
      <div className="flex items-center gap-2">
        {onSizeChange ? (
          <Select className="w-24" aria-label="Số dòng mỗi trang" value={size} onChange={(e) => onSizeChange(Number(e.target.value))}>
            {PAGE_SIZES.map((s) => (
              <option key={s} value={s}>
                {s} / trang
              </option>
            ))}
          </Select>
        ) : null}
        <Button size="icon" aria-label="Trang trước" disabledReason={page <= 1 ? 'Đang ở trang đầu.' : null} onClick={() => onPageChange(page - 1)}>
          <ChevronLeft />
        </Button>
        <span className="min-w-16 text-center tabular-nums">
          {page} / {pages}
        </span>
        <Button size="icon" aria-label="Trang sau" disabledReason={page >= pages ? 'Đang ở trang cuối.' : null} onClick={() => onPageChange(page + 1)}>
          <ChevronRight />
        </Button>
      </div>
    </div>
  )
}
