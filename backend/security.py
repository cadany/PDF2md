"""
统一安全校验模块
包含输入验证、清理、安全检查等功能
"""
import re
import html
import os
import secrets
import hashlib
from functools import wraps
from flask import request, jsonify, abort, session, g
from werkzeug.utils import secure_filename


class SecurityValidator:
    """安全验证器类"""
    
    # 禁止的文件扩展名
    DANGEROUS_EXTENSIONS = {
        '.exe', '.bat', '.cmd', '.com', '.pif', '.scr', '.vbs', '.js', 
        '.jar', '.sh', '.php', '.pl', '.py', '.rb', '.sql', '.jsp', 
        '.asp', '.aspx', '.cgi', '.msi', '.dll', '.so', '.dylib'
    }
    
    # 安全的文件扩展名
    SAFE_PDF_EXTENSIONS = {'.pdf'}
    
    # SQL注入检测模式
    SQL_INJECTION_PATTERNS = [
        r"(?i)(union\s+select)",
        r"(?i)(drop\s+table)",
        r"(?i)(create\s+table)",
        r"(?i)(insert\s+into)",
        r"(?i)(delete\s+from)",
        r"(?i)(update\s+\w+\s+set)",
        r"(?i)(exec\s*\()",
        r"(?i)(execute\s*\()",
        r"(?i)(sp_)",
        r"(?i)(;|--|/\*|\*/|xp_)",
        r"(?i)(\bselect\b|\bfrom\b|\bwhere\b|\border\s+by\b|\bgroup\s+by\b|\bhaving\b)",
    ]
    
    # XSS检测模式
    XSS_PATTERNS = [
        r"(?i)<script",
        r"(?i)</script>",
        r"(?i)javascript:",
        r"(?i)vbscript:",
        r"(?i)on\w+\s*=",
        r"(?i)expression\s*\(",
        r"(?i)eval\s*\(",
        r"(?i)alert\s*\(",
        r"(?i)<iframe",
        r"(?i)</iframe>",
        r"(?i)<object",
        r"(?i)</object>",
        r"(?i)<embed",
        r"(?i)</embed>",
        r"(?i)data:",
    ]
    
    # 命令注入检测模式
    COMMAND_INJECTION_PATTERNS = [
        r"(?i)(\|)",
        r"(?i)(;)",
        r"(?i)(`)",
        r"(?i)(&&)",
        r"(?i)(\|\|)",
        r"(?i)(\bcurl\b|\bwget\b|\bnc\b|\bncat\b|\btelnet\b)",
        r"(?i)(\bcat\b|\bless\b|\bmore\b|\bhead\b|\btail\b)",
        r"(?i)(\bsh\b|\bbash\b|\bpowershell\b|\bcmd\b)",
        r"(?i)(\bchmod\b|\bchown\b|\bkill\b|\bps\b|\bls\b|\bcp\b|\bm\b|\brm\b)",
        r"(?i)(\bnc\b|\bnetcat\b|\bsocat\b|\bnmap\b)",
        r"(?i)(\$\(|\${)",
    ]
    
    @staticmethod
    def sanitize_input(input_data):
        """清理输入数据"""
        if isinstance(input_data, str):
            # HTML转义
            sanitized = html.escape(input_data)
            # 移除潜在的危险字符
            sanitized = re.sub(r'[<>"\']', '', sanitized)
            return sanitized
        elif isinstance(input_data, dict):
            sanitized_dict = {}
            for key, value in input_data.items():
                sanitized_dict[key] = SecurityValidator.sanitize_input(value)
            return sanitized_dict
        elif isinstance(input_data, list):
            return [SecurityValidator.sanitize_input(item) for item in input_data]
        else:
            return input_data
    
    @staticmethod
    def validate_sql_injection(input_data):
        """检测SQL注入"""
        if isinstance(input_data, str):
            for pattern in SecurityValidator.SQL_INJECTION_PATTERNS:
                if re.search(pattern, input_data):
                    return False
        elif isinstance(input_data, dict):
            for value in input_data.values():
                if not SecurityValidator.validate_sql_injection(value):
                    return False
        elif isinstance(input_data, list):
            for item in input_data:
                if not SecurityValidator.validate_sql_injection(item):
                    return False
        return True
    
    @staticmethod
    def validate_xss(input_data):
        """检测XSS攻击"""
        if isinstance(input_data, str):
            for pattern in SecurityValidator.XSS_PATTERNS:
                if re.search(pattern, input_data):
                    return False
        elif isinstance(input_data, dict):
            for value in input_data.values():
                if not SecurityValidator.validate_xss(value):
                    return False
        elif isinstance(input_data, list):
            for item in input_data:
                if not SecurityValidator.validate_xss(item):
                    return False
        return True
    
    @staticmethod
    def validate_command_injection(input_data):
        """检测命令注入"""
        if isinstance(input_data, str):
            for pattern in SecurityValidator.COMMAND_INJECTION_PATTERNS:
                if re.search(pattern, input_data):
                    return False
        elif isinstance(input_data, dict):
            for value in input_data.values():
                if not SecurityValidator.validate_command_injection(value):
                    return False
        elif isinstance(input_data, list):
            for item in input_data:
                if not SecurityValidator.validate_command_injection(item):
                    return False
        return True
    
    @staticmethod
    def validate_filename(filename):
        """验证文件名安全"""
        # 使用Werkzeug的安全文件名函数
        safe_filename = secure_filename(filename)
        
        # 检查扩展名
        _, ext = os.path.splitext(safe_filename.lower())
        if ext in SecurityValidator.DANGEROUS_EXTENSIONS:
            return False, "危险的文件类型"
        
        # 检查路径遍历
        if '..' in safe_filename or '/' in safe_filename or '\\' in safe_filename:
            return False, "非法文件名"
        
        return True, safe_filename
    
    @staticmethod
    def validate_pdf_file(file):
        """验证PDF文件"""
        if not file or file.filename == '':
            return False, "未选择文件"
        
        # 验证文件名
        is_valid, result = SecurityValidator.validate_filename(file.filename)
        if not is_valid:
            return False, result
        
        # 检查扩展名
        _, ext = os.path.splitext(result.lower())
        if ext not in SecurityValidator.SAFE_PDF_EXTENSIONS:
            return False, "仅支持PDF文件"
        
        return True, result
    
    @staticmethod
    def generate_csrf_token():
        """生成CSRF令牌"""
        if 'csrf_token' not in session:
            session['csrf_token'] = secrets.token_hex(32)
        return session['csrf_token']
    
    @staticmethod
    def validate_csrf_token():
        """验证CSRF令牌"""
        token = request.headers.get('X-CSRF-Token') or request.form.get('csrf_token') or request.args.get('csrf_token')
        if not token:
            return False
        return token == session.get('csrf_token')
    
    @staticmethod
    def validate_idor(user_id, resource_owner_id):
        """验证IDOR（不安全的直接对象引用）"""
        # 在实际应用中，这里应该根据业务逻辑验证用户是否有权限访问资源
        # 例如，验证当前用户是否是资源的所有者
        return str(user_id) == str(resource_owner_id)
    
    @staticmethod
    def validate_rate_limit(request, limit=100, window=3600):
        """验证请求频率限制"""
        # 这是一个简化的实现，实际应用中需要使用Redis或数据库来跟踪请求
        # 这里我们简单地检查用户IP的请求频率
        client_ip = request.remote_addr
        key = f"rate_limit:{client_ip}"
        # 在实际应用中，这里会检查缓存或数据库中该IP的请求次数
        return True  # 简化返回，实际实现会更复杂


def csrf_protect(f):
    """CSRF保护装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        import json
        # 对于非GET、HEAD、OPTIONS、TRACE请求，验证CSRF令牌
        if request.method not in ['GET', 'HEAD', 'OPTIONS', 'TRACE']:
            if not SecurityValidator.validate_csrf_token():
                return jsonify({'error': 'CSRF验证失败', 'status': 'security_violation'}), 403
        
        # 对于所有请求，确保CSRF令牌存在
        token = SecurityValidator.generate_csrf_token()
        
        # 执行原始函数
        response = f(*args, **kwargs)
        
        # 对于GET请求，将CSRF令牌添加到响应中
        if request.method in ['GET', 'HEAD', 'OPTIONS', 'TRACE']:
            from flask import make_response
            # 如果response不是Response对象，将其转换为Response对象
            if not hasattr(response, 'status_code') or not hasattr(response, 'headers'):
                # 这意味着它可能是一个元组 (data, status_code) 或直接数据
                if isinstance(response, tuple):
                    data, status_code = response[0], response[1] if len(response) > 1 else 200
                    response_obj = make_response(jsonify(data), status_code)
                else:
                    response_obj = make_response(jsonify(response), 200)
                response = response_obj
            # 添加CSRF令牌到响应头
            response.headers['X-CSRF-Token'] = token
        
        return response
    return decorated_function


def idor_check(owner_field='user_id'):
    """IDOR检查装饰器"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 这里需要根据实际业务逻辑来实现IDOR检查
            # 例如，从session中获取当前用户ID，从请求参数或资源中获取资源所有者ID
            # 然后验证用户是否有权限访问该资源
            current_user_id = session.get('user_id')  # 假设用户ID存储在session中
            if current_user_id:
                # 从URL参数或请求体中获取资源ID
                resource_id = kwargs.get('id') or request.view_args.get('id') or request.args.get('id')
                if resource_id:
                    # 这里需要查询数据库获取资源的所有者ID
                    # 简化实现：假设所有者ID存储在g对象中（需要在路由中设置）
                    resource_owner_id = getattr(g, 'resource_owner_id', None)
                    if resource_owner_id and not SecurityValidator.validate_idor(current_user_id, resource_owner_id):
                        return jsonify({'error': 'IDOR检测：无权限访问资源', 'status': 'security_violation'}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def security_check(f):
    """装饰器：对所有请求进行安全检查"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 检查请求数据
        if request.is_json:
            # 检查JSON数据
            json_data = request.get_json()
            if json_data:
                if not SecurityValidator.validate_sql_injection(json_data):
                    return jsonify({'error': '检测到SQL注入尝试', 'status': 'security_violation'}), 400
                if not SecurityValidator.validate_xss(json_data):
                    return jsonify({'error': '检测到XSS尝试', 'status': 'security_violation'}), 400
                if not SecurityValidator.validate_command_injection(json_data):
                    return jsonify({'error': '检测到命令注入尝试', 'status': 'security_violation'}), 400
        elif request.form:
            # 检查表单数据
            form_data = dict(request.form)
            if not SecurityValidator.validate_sql_injection(form_data):
                return jsonify({'error': '检测到SQL注入尝试', 'status': 'security_violation'}), 400
            if not SecurityValidator.validate_xss(form_data):
                return jsonify({'error': '检测到XSS尝试', 'status': 'security_violation'}), 400
            if not SecurityValidator.validate_command_injection(form_data):
                return jsonify({'error': '检测到命令注入尝试', 'status': 'security_violation'}), 400
        
        # 检查URL参数
        args_data = dict(request.args)
        if not SecurityValidator.validate_sql_injection(args_data):
            return jsonify({'error': '检测到SQL注入尝试', 'status': 'security_violation'}), 400
        if not SecurityValidator.validate_xss(args_data):
            return jsonify({'error': '检测到XSS尝试', 'status': 'security_violation'}), 400
        if not SecurityValidator.validate_command_injection(args_data):
            return jsonify({'error': '检测到命令注入尝试', 'status': 'security_violation'}), 400
        
        # 检查文件上传
        if request.files:
            for file_key, file in request.files.items():
                if file and file.filename != '':
                    is_valid, result = SecurityValidator.validate_pdf_file(file)
                    if not is_valid:
                        return jsonify({'error': result, 'status': 'security_violation'}), 400
        
        # 检查请求频率限制（简化实现）
        if not SecurityValidator.validate_rate_limit(request):
            return jsonify({'error': '请求频率超限', 'status': 'rate_limit_exceeded'}), 429
        
        return f(*args, **kwargs)
    
    return decorated_function


def validate_input_types(data, expected_types):
    """
    验证输入数据类型
    :param data: 要验证的数据
    :param expected_types: 期望的类型列表，例如 {'name': str, 'age': int}
    :return: (is_valid, error_message)
    """
    for field, expected_type in expected_types.items():
        if field in data:
            value = data[field]
            if not isinstance(value, expected_type):
                # 尝试类型转换
                try:
                    if expected_type == int:
                        data[field] = int(value)
                    elif expected_type == float:
                        data[field] = float(value)
                    elif expected_type == str:
                        data[field] = str(value)
                    elif expected_type == bool:
                        data[field] = bool(value)
                except (ValueError, TypeError):
                    return False, f"字段 '{field}' 类型错误，期望 {expected_type.__name__}"
    
    return True, None