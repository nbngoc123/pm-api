# PM-KPI Web

Giao diện web cho hệ thống Quản lý dự án và KPI. Gọi API của backend trong `../be`.

React 19, Vite, TypeScript, Tailwind CSS 4, Radix UI, TanStack Query và Table, dnd-kit.

## Chạy

Cần backend chạy ở `http://127.0.0.1:8000` (xem `../be/README.md`). Vite chuyển tiếp mọi request `/api` sang đó; đổi địa chỉ bằng biến môi trường `VITE_API_TARGET`.

```bash
npm install
npm run dev        # http://localhost:5173
```

| Lệnh | Việc |
|---|---|
| `npm run dev` | Chạy máy chủ phát triển |
| `npm run build` | Kiểm tra kiểu và đóng gói vào `dist/` |
| `npm run lint` | Chạy oxlint |
| `npm run gen:api` | Sinh lại `src/api/schema.d.ts` từ `../be/docs/openapi.json` |

## Cấu trúc

```
src/
  api/          client.ts (fetch, token, tự làm mới phiên, lỗi) · schema.d.ts (tự sinh) · types.ts
  auth/         AuthProvider, useAuth (người dùng và quyền cấp hệ thống)
  components/
    ui/         nút, ô nhập, nhãn, hộp thoại, khung trượt, tooltip
    layout/     AppShell (thanh điều hướng), Page (tiêu đề, breadcrumb), thông báo, menu tài khoản
  features/
    admin/      quản trị tài khoản: tạo theo vai trò, khóa, đặt lại mật khẩu
    auth/       đăng nhập, đổi mật khẩu
    dashboard/  bảng điều khiển cá nhân
    projects/   danh sách, tổng quan, mốc, thành viên
    tasks/      Kanban, bảng, ưu tiên, chờ duyệt, khung chi tiết, ghi giờ
    timesheets/ giờ làm của tôi
  lib/          định dạng ngày giờ, nhãn tiếng Việt cho enum, tiện ích
```

## Quy ước

- **Phân quyền:** menu và màn hình không có quyền thì ẩn hẳn. Nút hành động trong trang thì hiện mờ kèm tooltip nêu lý do (`disabledReason` của `Button`). Backend vẫn kiểm tra lại mọi thao tác.
- **Luật chuyển trạng thái công việc** nằm ở `features/tasks/rules.ts`, phản chiếu `be/app/services/tasks.py`. Kanban, bảng và khung chi tiết đều dùng chung file này.
- **Thời gian:** backend trả thời điểm theo UTC không có hậu tố `Z`; luôn đọc qua `parseUtc` trong `lib/format.ts`.
- **Lỗi:** hiển thị `message` của backend; lỗi 422 theo từng ô nhập lấy qua `toFormErrors`.
- **Khóa lạc quan:** sửa công việc phải gửi kèm `version`; gặp `409 VERSION_CONFLICT` thì dữ liệu được tải lại.

## Chưa làm

KPI, vi phạm, tiến độ (EVM, burn-down), báo cáo portfolio.

Không có tự đăng ký: backend chỉ cho quản trị viên tạo tài khoản (`POST /users`).
