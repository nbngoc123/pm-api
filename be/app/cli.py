"""python -m app.cli scan-alerts | seed | snapshot-all  (gọi từ cron / k8s CronJob hằng ngày)."""
import sys

from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app.enums import TrangThaiDuAn
from app.models import DuAn
from app.seed import seed
from app.services import progress


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    with SessionLocal() as db:
        if cmd == "seed":
            Base.metadata.create_all(engine) if engine.dialect.name == "sqlite" else None
            seed(db)
        elif cmd == "scan-alerts":
            print(progress.scan_alerts(db))
        elif cmd == "snapshot-all":
            for p in db.scalars(select(DuAn).where(DuAn.trang_thai == TrangThaiDuAn.ACTIVE)):
                progress.take_snapshot(db, None, p)
        else:
            print(__doc__); sys.exit(1)
        db.commit()


if __name__ == "__main__":
    main()
