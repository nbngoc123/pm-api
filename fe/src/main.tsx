import { MutationCache, QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { toast, Toaster } from 'sonner'
import { ApiError } from '@/api/client'
import { AuthProvider } from '@/auth/AuthProvider'
import { TooltipProvider } from '@/components/ui/tooltip'
import { App } from './App'
import './index.css'

// Áp dụng giao diện tối trước khi vẽ để tránh nháy màu.
document.documentElement.classList.toggle('dark', localStorage.getItem('pmkpi.dark') === 'true')

const queryClient: QueryClient = new QueryClient({
  // Mọi thao tác ghi bị 409 VERSION_CONFLICT đều báo ở đây, kèm nút tải lại dữ liệu.
  mutationCache: new MutationCache({
    onError: (error) => {
      if (error instanceof ApiError && error.code === 'VERSION_CONFLICT') {
        toast.error('Dữ liệu đã bị người khác cập nhật. Vui lòng tải lại!', {
          id: 'version-conflict',
          duration: 15_000,
          action: { label: 'Tải lại', onClick: () => queryClient.invalidateQueries() },
        })
      }
    },
  }),
  defaultOptions: {
    queries: {
      staleTime: 15_000,
      refetchOnWindowFocus: true,
      // Lỗi 4xx là lỗi nghiệp vụ hoặc phân quyền, thử lại không giúp gì.
      retry: (count, error) => !(error instanceof ApiError && error.status >= 400 && error.status < 500) && count < 2,
    },
  },
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <TooltipProvider delayDuration={200}>
            <App />
            <Toaster position="bottom-right" richColors closeButton />
          </TooltipProvider>
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
)
