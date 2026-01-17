from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import os
import sys
import logging
import logging.config

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from routes.file_routes import file_router
from config import get_config

# 加载日志配置
log_config_path = os.path.join(os.path.dirname(__file__), 'logging.conf')
if os.path.exists(log_config_path):
    logging.config.fileConfig(log_config_path)
else:
    # 如果配置文件不存在，则使用基本配置
    logging.basicConfig(level=logging.INFO)

# 获取日志记录器
logger = logging.getLogger("uvicorn.access")


# 初始化配置
config = get_config()

# FastAPI应用配置
app = FastAPI(
    title="FileConverter API",
    version="1.0.0",
    description="文件转换API",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.get('security.cors_origins', ["*"]),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 自定义中间件：请求日志记录
@app.middleware("http")
async def log_requests(request, call_next):
    """记录请求日志的中间件"""
    import time
    
    start_time = time.time()
    
    # 记录请求信息
    logger.info(f"Request: {request.method} {request.url.path} - Client: {request.client.host if request.client else 'unknown'}")
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # 记录响应信息
        logger.info(f"Response: {request.method} {request.url.path} - Status: {response.status_code} - Time: {process_time:.2f}s")
        
        # 添加处理时间到响应头
        response.headers["X-Process-Time"] = str(process_time)
        
        return response
    except Exception as exc:
        process_time = time.time() - start_time
        logger.error(f"Error: {request.method} {request.url.path} - Exception: {str(exc)} - Time: {process_time:.2f}s")
        raise

# 全局异常处理
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    """请求验证错误处理"""
    return JSONResponse(
        status_code=422,
        content={
            "detail": "请求参数验证失败",
            "errors": exc.errors(),
            "path": request.url.path,
            "method": request.method
        }
    )

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    """HTTP异常处理"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "status_code": exc.status_code,
            "path": request.url.path,
            "method": request.method
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """通用异常处理"""
    import traceback
    
    # 记录详细错误信息到日志
    logger.error(f"Unhandled exception: {str(exc)}")
    logger.error(f"Traceback: {traceback.format_exc()}")
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": "服务器内部错误",
            "error": str(exc) if os.environ.get('DEBUG') == 'True' else "Internal server error",
            "path": request.url.path,
            "method": request.method
        }
    )

# 注册路由
app.include_router(file_router, prefix="/api", tags=["file"])

@app.get("/", summary="API根路径", description="返回API基本信息")
async def root():
    """API根路径"""
    return {
        "message": "Welcome to FileConverter API",
        "status": "running",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health", summary="健康检查", description="检查API服务状态")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "timestamp": "2026-01-05T22:20:00Z"
    }

if __name__ == '__main__':
    import uvicorn
    import logging

    # 从配置中获取服务器设置
    server_config = config.get_server_config()
    host = server_config.get('host', '0.0.0.0')
    port = server_config.get('port', 18080)
    debug = server_config.get('debug', False)
    reload = server_config.get('reload', False)
    
    # 获取专门用于应用启动的日志记录器
    startup_logger = logging.getLogger("uvicorn.error")
    startup_logger.info(f"启动服务器: {host}:{port}")
    startup_logger.info(f"调试模式: {debug}")
    startup_logger.info(f"热重载: {reload}")
    
    uvicorn.run(
        app, 
        host=host, 
        port=port,
        log_config=log_config_path,  # 使用统一的日志配置
        reload=reload
    )

    