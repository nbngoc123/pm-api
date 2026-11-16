import { flexRender, getCoreRowModel, getSortedRowModel, useReactTable, type ColumnDef, type SortingState } from '@tanstack/react-table'
import { ArrowDown, ArrowUp } from 'lucide-react'
import { useSearchParams } from 'react-router-dom'
import { Pagination } from '@/components/ui/pagination'
import { useMemo, useState } from 'react'
import type { Task } from '@/api/types'
import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/misc'
import { PRIORITY, TASK_STATUS } from '@/lib/labels'
import { cn } from '@/lib/utils'
import { Assignees, Deadline, TaskActionButtons } from './TaskBits'
import { useTaskBoard } from './TaskBoardContext'

const PRIORITY_ORDER = { LOW: 0, MEDIUM: 1, HIGH: 2, CRITICAL: 3 }

interface TaskTableProps {
  tasks: Task[]
  /** Giữ nguyên thứ tự backend trả về (danh sách ưu tiên), không cho sắp xếp lại. */
  fixedOrder?: boolean
}

export function TaskTable({ tasks, fixedOrder }: TaskTableProps) {
  const { openTask } = useTaskBoard()
  const [sorting, setSorting] = useState<SortingState>([])
  const [params, setParams] = useSearchParams()
  const size = Number(params.get('size')) || 20
  const requestedPage = Number(params.get('page')) || 1

  const columns = useMemo<ColumnDef<Task>[]>(
    () => [
      { accessorKey: 'ten_cv', header: 'Công việc', cell: (c) => <span className="font-medium">{c.row.original.ten_cv}</span> },
      {
        accessorKey: 'trang_thai',
        header: 'Trạng thái',
        cell: (c) => <Badge tone={TASK_STATUS[c.row.original.trang_thai].tone}>{TASK_STATUS[c.row.original.trang_thai].text}</Badge>,
      },
      {
        accessorKey: 'uu_tien',
        header: 'Ưu tiên',
        sortingFn: (a, b) => PRIORITY_ORDER[a.original.uu_tien] - PRIORITY_ORDER[b.original.uu_tien],
        cell: (c) => <Badge tone={PRIORITY[c.row.original.uu_tien].tone}>{PRIORITY[c.row.original.uu_tien].text}</Badge>,
      },
      { id: 'assignees', header: 'Người làm', enableSorting: false, cell: (c) => <Assignees task={c.row.original} /> },
      { accessorKey: 'han_hoan_thanh', header: 'Hạn', sortUndefined: 'last', cell: (c) => <Deadline task={c.row.original} /> },
      { accessorKey: 'ty_le_hoan_thanh', header: 'Tiến độ', cell: (c) => <span className="tabular-nums">{c.row.original.ty_le_hoan_thanh}%</span> },
      {
        id: 'actions',
        header: '',
        enableSorting: false,
        cell: (c) => (
          <div className="flex justify-end gap-1.5">
            <TaskActionButtons task={c.row.original} />
          </div>
        ),
      },
    ],
    [],
  )

  const table = useReactTable({
    data: tasks,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    enableSorting: !fixedOrder,
    getRowId: (t) => String(t.ma_cv),
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  })

  const rows = table.getRowModel().rows
  const pages = Math.max(1, Math.ceil(rows.length / size))
  const page = Math.min(requestedPage, pages)
  const pageRows = rows.slice((page - 1) * size, page * size)
  const update = (changes: Record<string, string>) =>
    setParams(
      (prev) => {
        const next = new URLSearchParams(prev)
        for (const [k, v] of Object.entries(changes)) next.set(k, v)
        return next
      },
      { replace: true },
    )

  return (
    <>
    <Card className="overflow-x-auto">
      <table className="w-full text-left">
        <thead className="border-b bg-surface-2 text-xs text-muted">
          {table.getHeaderGroups().map((group) => (
            <tr key={group.id}>
              {group.headers.map((h) => {
                const sorted = h.column.getIsSorted()
                return (
                  <th key={h.id} className="px-3 py-2 font-medium whitespace-nowrap" aria-sort={sorted === 'asc' ? 'ascending' : sorted === 'desc' ? 'descending' : undefined}>
                    {h.column.getCanSort() ? (
                      <button type="button" className="inline-flex items-center gap-1 hover:text-fg" onClick={h.column.getToggleSortingHandler()}>
                        {flexRender(h.column.columnDef.header, h.getContext())}
                        {sorted === 'asc' ? <ArrowUp className="size-3" /> : sorted === 'desc' ? <ArrowDown className="size-3" /> : null}
                      </button>
                    ) : (
                      flexRender(h.column.columnDef.header, h.getContext())
                    )}
                  </th>
                )
              })}
            </tr>
          ))}
        </thead>
        <tbody>
          {pageRows.map((row) => (
            <tr
              key={row.id}
              tabIndex={0}
              onClick={() => openTask(row.original.ma_cv)}
              onKeyDown={(e) => e.key === 'Enter' && e.target === e.currentTarget && openTask(row.original.ma_cv)}
              className={cn('cursor-pointer border-b last:border-0 hover:bg-surface-2', row.original.trang_thai === 'CANCELLED' && 'text-subtle')}
            >
              {row.getVisibleCells().map((cell) => (
                <td key={cell.id} className="px-3 py-2">
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
    <Pagination
      page={page}
      size={size}
      total={rows.length}
      onPageChange={(p) => update({ page: String(p) })}
      onSizeChange={(s) => update({ size: String(s), page: '1' })}
    />
    </>
  )
}
