from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppError(Exception):
    def __init__(self, status: int, code: str, message: str = "", details=None):
        self.status, self.code, self.message, self.details = status, code, message or code, details


def bad(code, msg="", details=None): return AppError(400, code, msg, details)
def unauthorized(code="UNAUTHORIZED", msg="Chưa đăng nhập hoặc token không hợp lệ"): return AppError(401, code, msg)
def forbidden(code="FORBIDDEN", msg="Không đủ quyền thực hiện thao tác này"): return AppError(403, code, msg)
def not_found(code="NOT_FOUND", msg="Không tìm thấy dữ liệu"): return AppError(404, code, msg)
def conflict(code, msg=""): return AppError(409, code, msg)
def invalid(code, msg="", details=None): return AppError(422, code, msg, details)


def _body(code, message, details=None):
    return {"error": {"code": code, "message": message, "details": details}}


def install_handlers(app: FastAPI):
    @app.exception_handler(AppError)
    async def _app(_: Request, e: AppError):
        return JSONResponse(status_code=e.status, content=_body(e.code, e.message, e.details))

    @app.exception_handler(RequestValidationError)
    async def _val(_: Request, e: RequestValidationError):
        det = [{"field": ".".join(str(x) for x in err["loc"][1:]), "message": err["msg"]} for err in e.errors()]
        return JSONResponse(status_code=422, content=_body("VALIDATION_ERROR", "Dữ liệu không hợp lệ", det))

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, e: StarletteHTTPException):
        code = {404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED"}.get(e.status_code, "HTTP_ERROR")
        return JSONResponse(status_code=e.status_code, content=_body(code, str(e.detail)))
