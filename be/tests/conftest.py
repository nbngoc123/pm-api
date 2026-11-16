import os, tempfile

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ["PASSWORD_ITERATIONS"] = "1000"
os.environ["UPLOAD_DIR"] = tempfile.mkdtemp()

from datetime import date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db, make_engine
from app.enums import LoaiNguoiDung
from app.main import API, create_app
from app.models import NguoiDung, NhanVien, QuanLy, VaiTro
from app.security import create_token, hash_password, utcnow
from app.seed import seed
from app.services.common import today

PW = "Passw0rd!"


class Ctx:
    def __init__(self, client, Session):
        self.c, self.S = client, Session
        self.u: dict[str, int] = {}
        self.tok: dict[str, str] = {}

    # ---- users ----
    def mk_user(self, key, role="EMPLOYEE", loai=None, mgr=None, rate=0, email=None):
        with self.S() as db:
            rid = db.scalar(select(VaiTro.ma_vai_tro).where(VaiTro.code == role))
            loai = loai or (LoaiNguoiDung.QUAN_LY if role in ("ADMIN", "DIRECTOR", "MANAGER") else LoaiNguoiDung.NHAN_VIEN)
            u = NguoiDung(email=email or f"{key}@t.vn", ho_ten=f"User {key}", mat_khau_hash=hash_password(PW),
                          ma_vai_tro_he_thong=rid, loai=loai)
            db.add(u); db.flush()
            if loai == LoaiNguoiDung.QUAN_LY:
                db.add(QuanLy(ma_nd=u.ma_nd))
            else:
                db.add(NhanVien(ma_nd=u.ma_nd, ma_quan_ly=self.u.get(mgr) if isinstance(mgr, str) else mgr, don_gia_gio=rate))
            db.commit()
            self.u[key] = u.ma_nd
            self.tok[key] = create_token(u.ma_nd, "access", 0)
        return u.ma_nd

    def h(self, key):
        return {"Authorization": f"Bearer {self.tok[key]}"} if key else {}

    # ---- http ----
    def req(self, method, path, who=None, **kw):
        return self.c.request(method, API + path, headers=self.h(who), **kw)

    def get(self, p, who=None, **kw): return self.req("GET", p, who, **kw)
    def post(self, p, who=None, json=None, **kw): return self.req("POST", p, who, json=json, **kw)
    def put(self, p, who=None, json=None, **kw): return self.req("PUT", p, who, json=json, **kw)
    def patch(self, p, who=None, json=None, **kw): return self.req("PATCH", p, who, json=json, **kw)
    def delete(self, p, who=None, **kw): return self.req("DELETE", p, who, **kw)

    # ---- domain helpers ----
    def project(self, **over):
        body = dict(ten_du_an="Dự án Alpha", muc_tieu="Mục tiêu", ngay_bat_dau=str(today() - timedelta(days=30)),
                    ngay_ket_thuc_du_kien=str(today() + timedelta(days=60)), ngan_sach_gio=1000, ma_quan_ly=self.u["pm"])
        body.update(over)
        r = self.post("/projects", "director", body)
        assert r.status_code == 201, r.text
        return r.json()

    def setup_project(self, active=True):
        p = self.project()
        pid = p["ma_du_an"]
        for k, role in (("tl", "TEAM_LEAD"), ("m1", "MEMBER"), ("m2", "MEMBER")):
            assert self.post(f"/projects/{pid}/members", "pm", {"ma_nguoi_dung": self.u[k], "vai_tro": role}).status_code == 201
        if active:
            assert self.patch(f"/projects/{pid}/status", "pm", {"trang_thai": "ACTIVE"}).status_code == 200
        self.pid = pid
        return pid

    def task(self, pid=None, who="pm", **over):
        body = dict(ten_cv="Task A", gio_du_kien=8, han_hoan_thanh=str(today() + timedelta(days=10)))
        body.update(over)
        r = self.post(f"/projects/{pid or self.pid}/tasks", who, body)
        assert r.status_code == 201, r.text
        return r.json()

    def assign(self, ma_cv, user, who="tl", **kw):
        r = self.post(f"/tasks/{ma_cv}/assignments", who, {"ma_nd": self.u[user], **kw})
        assert r.status_code == 201, r.text
        return r.json()

    def go(self, ma_cv, status, who):
        r = self.post(f"/tasks/{ma_cv}/transition", who, {"trang_thai": status})
        assert r.status_code == 200, r.text
        return r.json()

    def done_task(self, user="m1", **over):
        t = self.task(**over)
        self.assign(t["ma_cv"], user)
        self.go(t["ma_cv"], "IN_PROGRESS", user)
        self.go(t["ma_cv"], "IN_REVIEW", user)
        r = self.post(f"/tasks/{t['ma_cv']}/review", "tl", {"ket_qua": "APPROVED"})
        assert r.status_code == 201, r.text
        return t["ma_cv"]

    def log(self, ma_cv, who="m1", start_h_ago=5, hours=2, **kw):
        s = utcnow().replace(microsecond=0) - timedelta(hours=start_h_ago)
        body = {"bat_dau": s.isoformat(), "ket_thuc": (s + timedelta(hours=hours)).isoformat(), **kw}
        return self.post(f"/tasks/{ma_cv}/timesheets", who, body)


@pytest.fixture
def ctx():
    engine = make_engine("sqlite://")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with Session() as db:
        seed(db); db.commit()
    app = create_app()

    def _db():
        db = Session()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback(); raise
        finally:
            db.close()

    app.dependency_overrides[get_db] = _db
    c = Ctx(TestClient(app), Session)
    with Session() as db:
        a = db.scalar(select(NguoiDung).where(NguoiDung.email == "admin@company.local"))
        c.u["admin"] = a.ma_nd; c.tok["admin"] = create_token(a.ma_nd, "access", 0)
    c.mk_user("director", "DIRECTOR")
    c.mk_user("pm", "MANAGER")
    c.mk_user("mgr2", "MANAGER")
    c.mk_user("tl", "EMPLOYEE", mgr="pm")
    c.mk_user("m1", "EMPLOYEE", mgr="pm", rate=100000)
    c.mk_user("m2", "EMPLOYEE", mgr="mgr2", rate=100000)
    c.mk_user("out", "EMPLOYEE")
    yield c
    engine.dispose()


@pytest.fixture
def proj(ctx):
    ctx.setup_project()
    return ctx
