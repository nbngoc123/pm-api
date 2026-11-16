-- PM-KPI schema (PostgreSQL) – sinh tự động từ models; nguồn chính thức là alembic/versions

CREATE TABLE quy_dinh_vi_pham (
	ma_qd SERIAL NOT NULL, 
	ten_quy_dinh VARCHAR(200) NOT NULL, 
	diem_tru NUMERIC(6, 2) NOT NULL, 
	tu_ngay DATE NOT NULL, 
	den_ngay DATE, 
	CONSTRAINT pk_quy_dinh_vi_pham PRIMARY KEY (ma_qd)
);

CREATE TABLE quyen (
	ma_quyen SERIAL NOT NULL, 
	code VARCHAR(64) NOT NULL, 
	ten_quyen VARCHAR(120) NOT NULL, 
	mo_ta VARCHAR(255), 
	CONSTRAINT pk_quyen PRIMARY KEY (ma_quyen), 
	CONSTRAINT uq_quyen_code UNIQUE (code)
);

CREATE TABLE tieu_chi_kpi (
	ma_tieu_chi SERIAL NOT NULL, 
	ten_tieu_chi VARCHAR(150) NOT NULL, 
	mo_ta_cach_tinh TEXT, 
	don_vi VARCHAR(30), 
	nguon_du_lieu VARCHAR(30) NOT NULL, 
	CONSTRAINT pk_tieu_chi_kpi PRIMARY KEY (ma_tieu_chi), 
	CONSTRAINT uq_tieu_chi_kpi_ten_tieu_chi UNIQUE (ten_tieu_chi)
);

CREATE TABLE vai_tro (
	ma_vai_tro SERIAL NOT NULL, 
	code VARCHAR(32) NOT NULL, 
	ten_vai_tro VARCHAR(100) NOT NULL, 
	pham_vi VARCHAR(30) NOT NULL, 
	CONSTRAINT pk_vai_tro PRIMARY KEY (ma_vai_tro), 
	CONSTRAINT uq_vai_tro_code UNIQUE (code)
);

CREATE TABLE nguoi_dung (
	ma_nd SERIAL NOT NULL, 
	email VARCHAR(255) NOT NULL, 
	ho_ten VARCHAR(150) NOT NULL, 
	mat_khau_hash VARCHAR(255) NOT NULL, 
	ma_vai_tro_he_thong INTEGER NOT NULL, 
	trang_thai VARCHAR(30) NOT NULL, 
	loai VARCHAR(30) NOT NULL, 
	token_version INTEGER NOT NULL, 
	so_lan_dang_nhap_sai INTEGER NOT NULL, 
	khoa_den TIMESTAMP WITHOUT TIME ZONE, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	CONSTRAINT pk_nguoi_dung PRIMARY KEY (ma_nd), 
	CONSTRAINT fk_nguoi_dung_ma_vai_tro_he_thong_vai_tro FOREIGN KEY(ma_vai_tro_he_thong) REFERENCES vai_tro (ma_vai_tro)
);

CREATE UNIQUE INDEX ix_nguoi_dung_email ON nguoi_dung (email);
CREATE INDEX ix_nguoi_dung_ma_vai_tro_he_thong ON nguoi_dung (ma_vai_tro_he_thong);
CREATE TABLE vai_tro_quyen (
	ma_vai_tro INTEGER NOT NULL, 
	ma_quyen INTEGER NOT NULL, 
	CONSTRAINT pk_vai_tro_quyen PRIMARY KEY (ma_vai_tro, ma_quyen), 
	CONSTRAINT fk_vai_tro_quyen_ma_vai_tro_vai_tro FOREIGN KEY(ma_vai_tro) REFERENCES vai_tro (ma_vai_tro), 
	CONSTRAINT fk_vai_tro_quyen_ma_quyen_quyen FOREIGN KEY(ma_quyen) REFERENCES quyen (ma_quyen)
);

CREATE TABLE quan_ly (
	ma_nd INTEGER NOT NULL, 
	CONSTRAINT pk_quan_ly PRIMARY KEY (ma_nd), 
	CONSTRAINT fk_quan_ly_ma_nd_nguoi_dung FOREIGN KEY(ma_nd) REFERENCES nguoi_dung (ma_nd)
);

CREATE TABLE du_an (
	ma_du_an SERIAL NOT NULL, 
	ten_du_an VARCHAR(200) NOT NULL, 
	muc_tieu TEXT, 
	ngay_bat_dau DATE NOT NULL, 
	ngay_ket_thuc_du_kien DATE NOT NULL, 
	ngan_sach_gio NUMERIC(12, 2) NOT NULL, 
	trang_thai VARCHAR(30) NOT NULL, 
	ngay_dong DATE, 
	ma_quan_ly INTEGER NOT NULL, 
	created_by INTEGER, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	version INTEGER NOT NULL, 
	CONSTRAINT pk_du_an PRIMARY KEY (ma_du_an), 
	CONSTRAINT uq_du_an_ten_du_an UNIQUE (ten_du_an), 
	CONSTRAINT fk_du_an_ma_quan_ly_quan_ly FOREIGN KEY(ma_quan_ly) REFERENCES quan_ly (ma_nd), 
	CONSTRAINT fk_du_an_created_by_nguoi_dung FOREIGN KEY(created_by) REFERENCES nguoi_dung (ma_nd)
);

CREATE INDEX ix_du_an_trang_thai ON du_an (trang_thai);
CREATE INDEX ix_du_an_ma_quan_ly ON du_an (ma_quan_ly);
CREATE TABLE nhan_vien (
	ma_nd INTEGER NOT NULL, 
	ma_quan_ly INTEGER, 
	don_gia_gio NUMERIC(12, 2) NOT NULL, 
	CONSTRAINT pk_nhan_vien PRIMARY KEY (ma_nd), 
	CONSTRAINT fk_nhan_vien_ma_nd_nguoi_dung FOREIGN KEY(ma_nd) REFERENCES nguoi_dung (ma_nd), 
	CONSTRAINT fk_nhan_vien_ma_quan_ly_quan_ly FOREIGN KEY(ma_quan_ly) REFERENCES quan_ly (ma_nd)
);

CREATE INDEX ix_nhan_vien_ma_quan_ly ON nhan_vien (ma_quan_ly);
CREATE TABLE chi_so_du_an (
	ma_cs SERIAL NOT NULL, 
	ma_du_an INTEGER NOT NULL, 
	ngay DATE NOT NULL, 
	pv NUMERIC(16, 2) NOT NULL, 
	ev NUMERIC(16, 2) NOT NULL, 
	ac NUMERIC(16, 2) NOT NULL, 
	spi NUMERIC(8, 3), 
	cpi NUMERIC(8, 3), 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	CONSTRAINT pk_chi_so_du_an PRIMARY KEY (ma_cs), 
	CONSTRAINT uq_chi_so_ngay UNIQUE (ma_du_an, ngay), 
	CONSTRAINT fk_chi_so_du_an_ma_du_an_du_an FOREIGN KEY(ma_du_an) REFERENCES du_an (ma_du_an)
);

CREATE INDEX ix_chi_so_du_an_ma_du_an ON chi_so_du_an (ma_du_an);
CREATE TABLE epic (
	ma_epic SERIAL NOT NULL, 
	ma_du_an INTEGER NOT NULL, 
	ten_epic VARCHAR(200) NOT NULL, 
	mo_ta TEXT, 
	trang_thai VARCHAR(30) NOT NULL, 
	CONSTRAINT pk_epic PRIMARY KEY (ma_epic), 
	CONSTRAINT fk_epic_ma_du_an_du_an FOREIGN KEY(ma_du_an) REFERENCES du_an (ma_du_an)
);

CREATE INDEX ix_epic_ma_du_an ON epic (ma_du_an);
CREATE TABLE ky_kpi (
	ma_ky SERIAL NOT NULL, 
	ma_du_an INTEGER NOT NULL, 
	ten_ky VARCHAR(120) NOT NULL, 
	tu_ngay DATE NOT NULL, 
	den_ngay DATE NOT NULL, 
	trang_thai VARCHAR(30) NOT NULL, 
	CONSTRAINT pk_ky_kpi PRIMARY KEY (ma_ky), 
	CONSTRAINT fk_ky_kpi_ma_du_an_du_an FOREIGN KEY(ma_du_an) REFERENCES du_an (ma_du_an)
);

CREATE INDEX ix_ky_kpi_ma_du_an ON ky_kpi (ma_du_an);
CREATE TABLE moc_du_an (
	ma_moc SERIAL NOT NULL, 
	ma_du_an INTEGER NOT NULL, 
	ten_moc VARCHAR(200) NOT NULL, 
	han_hoan_thanh DATE NOT NULL, 
	trang_thai VARCHAR(30) NOT NULL, 
	CONSTRAINT pk_moc_du_an PRIMARY KEY (ma_moc), 
	CONSTRAINT fk_moc_du_an_ma_du_an_du_an FOREIGN KEY(ma_du_an) REFERENCES du_an (ma_du_an)
);

CREATE INDEX ix_moc_du_an_ma_du_an ON moc_du_an (ma_du_an);
CREATE TABLE nhat_ky_he_thong (
	ma_log SERIAL NOT NULL, 
	ma_nguoi_thuc_hien INTEGER, 
	ma_du_an INTEGER, 
	thoi_diem TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	loai_su_kien VARCHAR(60) NOT NULL, 
	noi_dung TEXT, 
	doi_tuong VARCHAR(40), 
	ma_doi_tuong INTEGER, 
	CONSTRAINT pk_nhat_ky_he_thong PRIMARY KEY (ma_log), 
	CONSTRAINT fk_nhat_ky_he_thong_ma_nguoi_thuc_hien_nguoi_dung FOREIGN KEY(ma_nguoi_thuc_hien) REFERENCES nguoi_dung (ma_nd), 
	CONSTRAINT fk_nhat_ky_he_thong_ma_du_an_du_an FOREIGN KEY(ma_du_an) REFERENCES du_an (ma_du_an)
);

CREATE INDEX ix_nhat_ky_he_thong_thoi_diem ON nhat_ky_he_thong (thoi_diem);
CREATE INDEX ix_nhat_ky_he_thong_loai_su_kien ON nhat_ky_he_thong (loai_su_kien);
CREATE INDEX ix_nhat_ky_he_thong_ma_nguoi_thuc_hien ON nhat_ky_he_thong (ma_nguoi_thuc_hien);
CREATE INDEX ix_nhat_ky_he_thong_ma_du_an ON nhat_ky_he_thong (ma_du_an);
CREATE TABLE thanh_vien_du_an (
	ma_du_an INTEGER NOT NULL, 
	ma_nguoi_dung INTEGER NOT NULL, 
	ma_vai_tro INTEGER NOT NULL, 
	ngay_tham_gia DATE NOT NULL, 
	ngay_roi DATE, 
	trang_thai VARCHAR(30) NOT NULL, 
	CONSTRAINT pk_thanh_vien_du_an PRIMARY KEY (ma_du_an, ma_nguoi_dung), 
	CONSTRAINT fk_thanh_vien_du_an_ma_du_an_du_an FOREIGN KEY(ma_du_an) REFERENCES du_an (ma_du_an), 
	CONSTRAINT fk_thanh_vien_du_an_ma_nguoi_dung_nguoi_dung FOREIGN KEY(ma_nguoi_dung) REFERENCES nguoi_dung (ma_nd), 
	CONSTRAINT fk_thanh_vien_du_an_ma_vai_tro_vai_tro FOREIGN KEY(ma_vai_tro) REFERENCES vai_tro (ma_vai_tro)
);

CREATE TABLE cau_hinh_kpi (
	ma_ky INTEGER NOT NULL, 
	ma_tieu_chi INTEGER NOT NULL, 
	trong_so NUMERIC(6, 2) NOT NULL, 
	chi_tieu NUMERIC(12, 2) NOT NULL, 
	CONSTRAINT pk_cau_hinh_kpi PRIMARY KEY (ma_ky, ma_tieu_chi), 
	CONSTRAINT fk_cau_hinh_kpi_ma_ky_ky_kpi FOREIGN KEY(ma_ky) REFERENCES ky_kpi (ma_ky), 
	CONSTRAINT fk_cau_hinh_kpi_ma_tieu_chi_tieu_chi_kpi FOREIGN KEY(ma_tieu_chi) REFERENCES tieu_chi_kpi (ma_tieu_chi)
);

CREATE TABLE danh_gia_kpi (
	ma_ky INTEGER NOT NULL, 
	ma_nguoi_dung INTEGER NOT NULL, 
	ma_nguoi_duyet INTEGER, 
	trang_thai VARCHAR(30) NOT NULL, 
	ngay_xac_nhan DATE, 
	ngay_duyet DATE, 
	diem_goc NUMERIC(6, 2), 
	diem_tru NUMERIC(6, 2) NOT NULL, 
	diem_tong NUMERIC(6, 2), 
	nhan_xet TEXT, 
	CONSTRAINT pk_danh_gia_kpi PRIMARY KEY (ma_ky, ma_nguoi_dung), 
	CONSTRAINT fk_danh_gia_kpi_ma_ky_ky_kpi FOREIGN KEY(ma_ky) REFERENCES ky_kpi (ma_ky), 
	CONSTRAINT fk_danh_gia_kpi_ma_nguoi_dung_nguoi_dung FOREIGN KEY(ma_nguoi_dung) REFERENCES nguoi_dung (ma_nd), 
	CONSTRAINT fk_danh_gia_kpi_ma_nguoi_duyet_quan_ly FOREIGN KEY(ma_nguoi_duyet) REFERENCES quan_ly (ma_nd)
);

CREATE INDEX ix_danh_gia_kpi_ma_nguoi_dung ON danh_gia_kpi (ma_nguoi_dung);
CREATE TABLE task (
	ma_cv SERIAL NOT NULL, 
	ma_du_an INTEGER NOT NULL, 
	ma_moc INTEGER, 
	ma_epic INTEGER, 
	ten_cv VARCHAR(200) NOT NULL, 
	mo_ta TEXT, 
	trang_thai VARCHAR(30) NOT NULL, 
	uu_tien VARCHAR(30) NOT NULL, 
	ty_le_hoan_thanh INTEGER NOT NULL, 
	ngay_bat_dau_du_kien DATE, 
	han_hoan_thanh DATE, 
	gio_du_kien NUMERIC(10, 2) NOT NULL, 
	ma_nguoi_tao INTEGER NOT NULL, 
	hoan_thanh_luc TIMESTAMP WITHOUT TIME ZONE, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	version INTEGER NOT NULL, 
	CONSTRAINT pk_task PRIMARY KEY (ma_cv), 
	CONSTRAINT fk_task_ma_du_an_du_an FOREIGN KEY(ma_du_an) REFERENCES du_an (ma_du_an), 
	CONSTRAINT fk_task_ma_moc_moc_du_an FOREIGN KEY(ma_moc) REFERENCES moc_du_an (ma_moc), 
	CONSTRAINT fk_task_ma_epic_epic FOREIGN KEY(ma_epic) REFERENCES epic (ma_epic), 
	CONSTRAINT fk_task_ma_nguoi_tao_nguoi_dung FOREIGN KEY(ma_nguoi_tao) REFERENCES nguoi_dung (ma_nd)
);

CREATE INDEX ix_task_ma_du_an ON task (ma_du_an);
CREATE INDEX ix_task_ma_moc ON task (ma_moc);
CREATE INDEX ix_task_ma_epic ON task (ma_epic);
CREATE INDEX ix_task_project_status ON task (ma_du_an, trang_thai);
CREATE TABLE chi_tiet_kpi (
	ma_nguoi_dung INTEGER NOT NULL, 
	ma_ky INTEGER NOT NULL, 
	ma_tieu_chi INTEGER NOT NULL, 
	gia_tri_tu_dong NUMERIC(12, 2), 
	gia_tri_thu_cong NUMERIC(12, 2), 
	gia_tri_xac_nhan NUMERIC(12, 2), 
	ghi_chu TEXT, 
	CONSTRAINT pk_chi_tiet_kpi PRIMARY KEY (ma_nguoi_dung, ma_ky, ma_tieu_chi), 
	CONSTRAINT fk_chi_tiet_kpi_ma_ky_cau_hinh_kpi FOREIGN KEY(ma_ky, ma_tieu_chi) REFERENCES cau_hinh_kpi (ma_ky, ma_tieu_chi), 
	CONSTRAINT fk_chi_tiet_kpi_ma_ky_danh_gia_kpi FOREIGN KEY(ma_ky, ma_nguoi_dung) REFERENCES danh_gia_kpi (ma_ky, ma_nguoi_dung), 
	CONSTRAINT fk_chi_tiet_kpi_ma_nguoi_dung_nguoi_dung FOREIGN KEY(ma_nguoi_dung) REFERENCES nguoi_dung (ma_nd), 
	CONSTRAINT fk_chi_tiet_kpi_ma_ky_ky_kpi FOREIGN KEY(ma_ky) REFERENCES ky_kpi (ma_ky), 
	CONSTRAINT fk_chi_tiet_kpi_ma_tieu_chi_tieu_chi_kpi FOREIGN KEY(ma_tieu_chi) REFERENCES tieu_chi_kpi (ma_tieu_chi)
);

CREATE TABLE ke_hoach_goc (
	ma_cv INTEGER NOT NULL, 
	ngay_bat_dau_goc DATE NOT NULL, 
	ngay_ket_thuc_goc DATE NOT NULL, 
	gio_du_kien_goc NUMERIC(10, 2) NOT NULL, 
	chi_phi_ke_hoach_goc NUMERIC(14, 2) NOT NULL, 
	khoa_luc TIMESTAMP WITHOUT TIME ZONE, 
	CONSTRAINT pk_ke_hoach_goc PRIMARY KEY (ma_cv), 
	CONSTRAINT fk_ke_hoach_goc_ma_cv_task FOREIGN KEY(ma_cv) REFERENCES task (ma_cv)
);

CREATE TABLE nhat_ky_gio_lam (
	ma_nk SERIAL NOT NULL, 
	ma_cv INTEGER NOT NULL, 
	ma_nd INTEGER NOT NULL, 
	bat_dau TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	ket_thuc TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	so_gio NUMERIC(6, 2) NOT NULL, 
	noi_dung TEXT, 
	chi_phi_thuc_te NUMERIC(14, 2) NOT NULL, 
	CONSTRAINT pk_nhat_ky_gio_lam PRIMARY KEY (ma_nk), 
	CONSTRAINT fk_nhat_ky_gio_lam_ma_cv_task FOREIGN KEY(ma_cv) REFERENCES task (ma_cv), 
	CONSTRAINT fk_nhat_ky_gio_lam_ma_nd_nhan_vien FOREIGN KEY(ma_nd) REFERENCES nhan_vien (ma_nd)
);

CREATE INDEX ix_nhat_ky_gio_lam_ma_cv ON nhat_ky_gio_lam (ma_cv);
CREATE INDEX ix_timesheet_user_time ON nhat_ky_gio_lam (ma_nd, bat_dau);
CREATE INDEX ix_nhat_ky_gio_lam_ma_nd ON nhat_ky_gio_lam (ma_nd);
CREATE TABLE phan_cong (
	ma_cv INTEGER NOT NULL, 
	ma_nd INTEGER NOT NULL, 
	trang_thai_phan_cong VARCHAR(30) NOT NULL, 
	ngay_giao DATE NOT NULL, 
	gio_du_kien NUMERIC(10, 2) NOT NULL, 
	ma_nguoi_giao INTEGER NOT NULL, 
	CONSTRAINT pk_phan_cong PRIMARY KEY (ma_cv, ma_nd), 
	CONSTRAINT fk_phan_cong_ma_cv_task FOREIGN KEY(ma_cv) REFERENCES task (ma_cv), 
	CONSTRAINT fk_phan_cong_ma_nd_nhan_vien FOREIGN KEY(ma_nd) REFERENCES nhan_vien (ma_nd), 
	CONSTRAINT fk_phan_cong_ma_nguoi_giao_nguoi_dung FOREIGN KEY(ma_nguoi_giao) REFERENCES nguoi_dung (ma_nd)
);

CREATE INDEX ix_phan_cong_ma_nd ON phan_cong (ma_nd);
CREATE TABLE sub_task (
	ma_subtask SERIAL NOT NULL, 
	ma_cv INTEGER NOT NULL, 
	ten_subtask VARCHAR(200) NOT NULL, 
	mo_ta TEXT, 
	trang_thai VARCHAR(30) NOT NULL, 
	CONSTRAINT pk_sub_task PRIMARY KEY (ma_subtask), 
	CONSTRAINT fk_sub_task_ma_cv_task FOREIGN KEY(ma_cv) REFERENCES task (ma_cv)
);

CREATE INDEX ix_sub_task_ma_cv ON sub_task (ma_cv);
CREATE TABLE tep_dinh_kem (
	ma_tep SERIAL NOT NULL, 
	ma_cv INTEGER NOT NULL, 
	ten_tep VARCHAR(255) NOT NULL, 
	duong_dan VARCHAR(500) NOT NULL, 
	kich_thuoc INTEGER NOT NULL, 
	ma_nguoi_tai INTEGER NOT NULL, 
	thoi_diem_tai TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	CONSTRAINT pk_tep_dinh_kem PRIMARY KEY (ma_tep), 
	CONSTRAINT fk_tep_dinh_kem_ma_cv_task FOREIGN KEY(ma_cv) REFERENCES task (ma_cv), 
	CONSTRAINT fk_tep_dinh_kem_ma_nguoi_tai_nguoi_dung FOREIGN KEY(ma_nguoi_tai) REFERENCES nguoi_dung (ma_nd)
);

CREATE INDEX ix_tep_dinh_kem_ma_cv ON tep_dinh_kem (ma_cv);
CREATE TABLE thong_bao (
	ma_tb SERIAL NOT NULL, 
	ma_nd INTEGER NOT NULL, 
	loai VARCHAR(40) NOT NULL, 
	tieu_de VARCHAR(255) NOT NULL, 
	noi_dung TEXT, 
	ma_cv INTEGER, 
	da_doc BOOLEAN NOT NULL, 
	dedupe_key VARCHAR(120), 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	CONSTRAINT pk_thong_bao PRIMARY KEY (ma_tb), 
	CONSTRAINT fk_thong_bao_ma_nd_nguoi_dung FOREIGN KEY(ma_nd) REFERENCES nguoi_dung (ma_nd), 
	CONSTRAINT fk_thong_bao_ma_cv_task FOREIGN KEY(ma_cv) REFERENCES task (ma_cv), 
	CONSTRAINT uq_thong_bao_dedupe_key UNIQUE (dedupe_key)
);

CREATE INDEX ix_thong_bao_ma_nd ON thong_bao (ma_nd);
CREATE TABLE vi_pham (
	ma_vp SERIAL NOT NULL, 
	ma_cv INTEGER NOT NULL, 
	ma_nd INTEGER NOT NULL, 
	ma_nguoi_lap INTEGER NOT NULL, 
	ma_qd INTEGER NOT NULL, 
	noi_dung TEXT NOT NULL, 
	trang_thai VARCHAR(30) NOT NULL, 
	thoi_diem TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	han_giai_trinh TIMESTAMP WITHOUT TIME ZONE, 
	ngay_xu_ly DATE, 
	ket_luan TEXT, 
	ma_nguoi_xu_ly INTEGER, 
	ma_ky_ap_dung INTEGER, 
	CONSTRAINT pk_vi_pham PRIMARY KEY (ma_vp), 
	CONSTRAINT fk_vi_pham_ma_cv_task FOREIGN KEY(ma_cv) REFERENCES task (ma_cv), 
	CONSTRAINT fk_vi_pham_ma_nd_nhan_vien FOREIGN KEY(ma_nd) REFERENCES nhan_vien (ma_nd), 
	CONSTRAINT fk_vi_pham_ma_nguoi_lap_nguoi_dung FOREIGN KEY(ma_nguoi_lap) REFERENCES nguoi_dung (ma_nd), 
	CONSTRAINT fk_vi_pham_ma_qd_quy_dinh_vi_pham FOREIGN KEY(ma_qd) REFERENCES quy_dinh_vi_pham (ma_qd), 
	CONSTRAINT fk_vi_pham_ma_nguoi_xu_ly_quan_ly FOREIGN KEY(ma_nguoi_xu_ly) REFERENCES quan_ly (ma_nd), 
	CONSTRAINT fk_vi_pham_ma_ky_ap_dung_ky_kpi FOREIGN KEY(ma_ky_ap_dung) REFERENCES ky_kpi (ma_ky)
);

CREATE INDEX ix_vi_pham_trang_thai ON vi_pham (trang_thai);
CREATE INDEX ix_vi_pham_ma_ky_ap_dung ON vi_pham (ma_ky_ap_dung);
CREATE INDEX ix_vi_pham_ma_cv ON vi_pham (ma_cv);
CREATE INDEX ix_vi_pham_ma_nd ON vi_pham (ma_nd);
CREATE TABLE xet_duyet_cong_viec (
	ma_duyet SERIAL NOT NULL, 
	ma_cv INTEGER NOT NULL, 
	ma_nguoi_duyet INTEGER NOT NULL, 
	ket_qua VARCHAR(30) NOT NULL, 
	nhan_xet TEXT, 
	thoi_diem_duyet TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	CONSTRAINT pk_xet_duyet_cong_viec PRIMARY KEY (ma_duyet), 
	CONSTRAINT fk_xet_duyet_cong_viec_ma_cv_task FOREIGN KEY(ma_cv) REFERENCES task (ma_cv), 
	CONSTRAINT fk_xet_duyet_cong_viec_ma_nguoi_duyet_nguoi_dung FOREIGN KEY(ma_nguoi_duyet) REFERENCES nguoi_dung (ma_nd)
);

CREATE INDEX ix_xet_duyet_cong_viec_ma_cv ON xet_duyet_cong_viec (ma_cv);
CREATE TABLE giai_trinh (
	ma_gt SERIAL NOT NULL, 
	ma_vp INTEGER NOT NULL, 
	noi_dung TEXT NOT NULL, 
	thoi_diem_gui TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	duong_dan_bang_chung VARCHAR(500), 
	CONSTRAINT pk_giai_trinh PRIMARY KEY (ma_gt), 
	CONSTRAINT fk_giai_trinh_ma_vp_vi_pham FOREIGN KEY(ma_vp) REFERENCES vi_pham (ma_vp)
);

CREATE INDEX ix_giai_trinh_ma_vp ON giai_trinh (ma_vp);