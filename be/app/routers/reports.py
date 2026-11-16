from datetime import date

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import current_user, require_sys
from app.enums import TrangThaiDuAn
from app.errors import forbidden, invalid
from app.services import reports as svc
from app.services.access import require_project_perm, system_perms
from app.services.common import audit

router = APIRouter(tags=["6. Báo cáo & Dashboard"])


@router.get("/dashboard/me", summary="6.3 Dashboard cá nhân")
def dashboard(ma_da: int | None = None, tu_ngay: date | None = None, den_ngay: date | None = None,
              user=Depends(current_user), db: Session = Depends(get_db)):
    return svc.dashboard_me(db, user, ma_da, tu_ngay, den_ngay)


@router.get("/reports/portfolio", summary="6.4 Báo cáo portfolio đa dự án (Ban giám đốc)")
def portfolio(trang_thai: TrangThaiDuAn | None = None, ma_quan_ly: int | None = None, tu_ngay: date | None = None,
              den_ngay: date | None = None, suc_khoe: str | None = Query(None, pattern="^(GREEN|AMBER|RED|GREY)$"),
              user=Depends(require_sys("report.portfolio")), db: Session = Depends(get_db)):
    return svc.portfolio(db, trang_thai, ma_quan_ly, tu_ngay, den_ngay, suc_khoe)


@router.get("/reports/projects/{ma_da}", summary="6.2/6.4 Báo cáo tổng hợp một dự án")
def project_report(ma_da: int, user=Depends(current_user), db: Session = Depends(get_db)):
    return svc.project_report(db, require_project_perm(db, user, ma_da, "report.project"))


@router.get("/exports", summary="6.5 Xuất báo cáo (csv | xlsx) – chỉ Quản lý dự án (DFD: File báo cáo → Quản lý dự án)")
def export(ma_da: int, dataset: str = Query(..., pattern="^(tasks|timesheets|violations|kpi)$"),
           format: str = Query("csv", pattern="^(csv|xlsx)$"),
           user=Depends(current_user), db: Session = Depends(get_db)):
    require_project_perm(db, user, ma_da, "report.export")
    headers, rows = svc.dataset(db, dataset, ma_da)
    audit(db, user.ma_nd, "REPORT_EXPORTED", "report", ma_da, f"{dataset}.{format}")
    if format == "csv":
        body, mime = svc.to_csv(headers, rows), "text/csv; charset=utf-8"
    else:
        body, mime = svc.to_xlsx(headers, rows), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return Response(body, media_type=mime, headers={"Content-Disposition": f'attachment; filename="{dataset}.{format}"'})
