import { useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { api, errorMessage } from '@/api/client'
import type { Task } from '@/api/types'

/** Mở khung chi tiết của một task khi chỉ biết mã task (dashboard, giờ làm, thông báo). */
export function useOpenTask() {
  const navigate = useNavigate()
  return useCallback(
    async (taskId: number) => {
      try {
        const task = await api.get<Task>(`/tasks/${taskId}`)
        navigate(`/projects/${task.ma_du_an}/tasks?task=${task.ma_cv}`)
      } catch (e) {
        toast.error(errorMessage(e))
      }
    },
    [navigate],
  )
}
