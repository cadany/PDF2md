from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, status, Header, Path
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
import logging
from service.file_service import FileService
from service.convert_service import ConvertService

# 创建路由级别的日志记录器
logger = logging.getLogger("route.file_routes")

# 创建FastAPI路由器
file_router = APIRouter(prefix="/file", tags=["file"])

# 依赖注入
file_service = FileService()
convert_service = ConvertService(file_service)

def get_file_service() -> FileService:
    """获取文件服务实例"""
    return file_service

def get_convert_service() -> ConvertService:
    """获取转换服务实例"""
    return convert_service

async def api_key_auth(api_key: str = Header(..., alias="X-API-Key")):
    """API Key认证依赖"""
    # 验证API Key的逻辑
    valid_keys = [
        "12345", 
        "67890"
        ]  # 可以从环境变量或配置文件中读取
    if api_key not in valid_keys:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的API Key"
        )

@file_router.post(
    "/upload",
    status_code=status.HTTP_200_OK,
    summary="文件上传接口",
    description="上传文件到服务器"
)
async def upload_file(
    file: UploadFile = File(..., description="上传的文件"),
    file_service: FileService = Depends(get_file_service),
    _: str = Depends(api_key_auth)
) -> Dict[str, Any]:
    """
    文件上传接口
    """
    # 检查是否有文件上传
    if not file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="未提供文件"
        )
    
    if file.filename == "":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="未选择文件"
        )

    # 验证文件类型
    if not file_service.is_allowed_file(file.filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="文件类型不允许"
        )

    # 读取文件内容并保存
    try:
        file_content = await file.read()
        result = file_service.save_file(file_content, file.filename)
        
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"文件上传失败: {str(e)}"
        )

@file_router.delete(
    "/delete/{file_id}",
    status_code=status.HTTP_200_OK,
    summary="文件删除接口",
    description="根据文件ID删除服务器上的文件"
)
async def delete_file(
    file_id: str = Path(..., description="要删除的文件ID"),
    file_service: FileService = Depends(get_file_service),
    _: str = Depends(api_key_auth)
) -> Dict[str, Any]:
    """
    文件删除接口
    """
    try:
        logger.info(f"删除文件: {file_id}")
        result = file_service.delete_file(file_id)
        return result
    except Exception as e:
        logger.error(f"删除文件失败: {file_id}, 错误: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"文件删除失败: {str(e)}"
        )

@file_router.get(
    "/info/{file_id}",
    status_code=status.HTTP_200_OK,
    summary="文件信息查询接口",
    description="根据文件ID查询文件信息"
)
async def get_file_info(
    file_id: str = Path(..., description="要查询的文件ID"),
    file_service: FileService = Depends(get_file_service),
    _: str = Depends(api_key_auth)
) -> Dict[str, Any]:
    """
    文件信息查询接口
    """
    try:
        logger.info(f"查询文件信息: {file_id}")
        file_info = file_service.get_file_info(file_id)
        if file_info:
            return file_info
        else:
            logger.warning(f"文件不存在: {file_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"文件ID {file_id} 不存在"
            )
    except Exception as e:
        logger.error(f"查询文件信息失败: {file_id}, 错误: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"文件信息查询失败: {str(e)}"
        )

@file_router.get(
    "/list",
    status_code=status.HTTP_200_OK,
    summary="文件列表查询接口",
    description="查询服务器上所有已上传文件的信息"
)
async def list_files(
    file_service: FileService = Depends(get_file_service),
    _: str = Depends(api_key_auth)
) -> Dict[str, Any]:
    """
    文件列表查询接口
    """
    try:
        file_list = file_service.list_files()
        return file_list
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"文件列表查询失败: {str(e)}"
        )   

# 定义异步转换相关的数据模型
class ConvertTaskStartResponse(BaseModel):
    task_id: str = Field(..., description="转换任务ID")
    message: str = Field(..., description="任务启动消息")
    file_id: str = Field(..., description="文件ID")

class ConvertTaskRequest(BaseModel):
    file_id: str = Field(..., description="要转换的文件ID")

class ConvertTaskResultResponse(BaseModel):
    task_id: str = Field(..., description="转换任务ID")
    file_id: str = Field(..., description="文件ID")
    status: str = Field(..., description="任务状态: pending, processing, completed, failed")
    progress: int = Field(..., description="转换进度百分比")
    result: Optional[Dict[str, Any]] = Field(None, description="转换结果")
    error: Optional[str] = Field(None, description="错误信息")
    start_time: Optional[float] = Field(None, description="任务开始时间")
    end_time: Optional[float] = Field(None, description="任务结束时间")

@file_router.post(
    "/convert2md",
    status_code=status.HTTP_200_OK,
    summary="启动异步文件转换任务",
    description="根据文件ID启动异步文件转换为Markdown任务，返回任务ID"
)
async def start_convert_task(
    request: ConvertTaskRequest,
    convert_service: ConvertService = Depends(get_convert_service),
    _: str = Depends(api_key_auth)
) -> ConvertTaskStartResponse:
    """
    启动异步文件转换任务
    """
    try:
        task_id = convert_service.start_convert_task(request.file_id)
        
        return ConvertTaskStartResponse(
            task_id=task_id,
            message="转换任务已启动",
            file_id=request.file_id
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"启动转换任务失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_200_OK,
            detail=f"启动转换任务失败: {str(e)}"
        )

@file_router.get(
    "/convert2md/result/{task_id}",
    status_code=status.HTTP_200_OK,
    summary="查询转换任务结果",
    description="根据任务ID查询文件转换任务的结果"
)
async def get_convert_task_result(
    task_id: str = Path(..., description="转换任务ID"),
    convert_service: ConvertService = Depends(get_convert_service),
    _: str = Depends(api_key_auth)
) -> ConvertTaskResultResponse:
    """
    查询转换任务结果
    """
    try:
        logger.info(f"查询转换任务: {task_id}")
        task_status = convert_service.get_task_status(task_id)
        logger.info(f"查询转换任务结果: {task_status}")

        return ConvertTaskResultResponse(
            task_id=task_status['task_id'],
            file_id=task_status['file_id'],
            status=task_status['status'],
            progress=task_status['progress'],
            result=task_status['result'],
            error=task_status['error'],
            start_time=task_status['start_time'],
            end_time=task_status['end_time']
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_200_OK,
            detail=f"查询转换任务结果失败: {str(e)}"
        )
