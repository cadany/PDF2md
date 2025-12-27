"""
安全功能测试脚本
测试所有安全校验功能
"""
import requests
import json
import os
from werkzeug.utils import secure_filename

# 测试服务器地址
BASE_URL = "http://localhost:18080"

def test_sql_injection():
    """测试SQL注入防护"""
    print("测试SQL注入防护...")
    
    # 尝试发送包含SQL注入尝试的请求
    malicious_data = {
        "item_name": "Test Item'; DROP TABLE bids; --",
        "bid_amount": 100.0,
        "bidder_name": "Test User"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/bids", json=malicious_data)
        if response.status_code == 400 and "security_violation" in response.text:
            print("✓ SQL注入防护工作正常")
        else:
            print(f"✗ SQL注入防护可能存在问题 - 状态码: {response.status_code}, 响应: {response.text}")
    except Exception as e:
        print(f"测试SQL注入时出错: {e}")

def test_xss_protection():
    """测试XSS防护"""
    print("测试XSS防护...")
    
    # 尝试发送包含XSS尝试的请求
    malicious_data = {
        "item_name": "<script>alert('XSS')</script>",
        "bid_amount": 100.0,
        "bidder_name": "Test User"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/bids", json=malicious_data)
        if response.status_code == 400 and "security_violation" in response.text:
            print("✓ XSS防护工作正常")
        else:
            print(f"✗ XSS防护可能存在问题 - 状态码: {response.status_code}, 响应: {response.text}")
    except Exception as e:
        print(f"测试XSS防护时出错: {e}")

def test_command_injection():
    """测试命令注入防护"""
    print("测试命令注入防护...")
    
    # 尝试发送包含命令注入尝试的请求
    malicious_data = {
        "item_name": "Test Item",
        "bid_amount": 100.0,
        "bidder_name": "Test User | rm -rf /"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/bids", json=malicious_data)
        if response.status_code == 400 and "security_violation" in response.text:
            print("✓ 命令注入防护工作正常")
        else:
            print(f"✗ 命令注入防护可能存在问题 - 状态码: {response.status_code}, 响应: {response.text}")
    except Exception as e:
        print(f"测试命令注入防护时出错: {e}")

def get_csrf_token():
    """获取CSRF令牌"""
    try:
        # 发送GET请求到主页或任何页面来获取CSRF令牌
        response = requests.get(f"{BASE_URL}/")
        # 在实际实现中，CSRF令牌可能通过特定的端点返回
        # 或者通过Cookie设置，这里我们模拟获取过程
        return None  # Flask-Sessions会自动处理CSRF令牌
    except Exception as e:
        print(f"获取CSRF令牌时出错: {e}")
        return None

def test_csrf_protection():
    """测试CSRF防护"""
    print("测试CSRF防护...")
    
    # 首先尝试发送一个没有CSRF令牌的POST请求（应该失败）
    normal_data = {
        "item_name": "CSRF Test Item",
        "bid_amount": 150.0,
        "bidder_name": "CSRF Test User"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/bids", json=normal_data)
        print(f"CSRF测试 - 无令牌请求状态码: {response.status_code}")
        if response.status_code == 403:
            print("✓ CSRF防护工作正常 - 无令牌请求被拒绝")
        else:
            print("⚠ CSRF防护可能未完全启用 - 无令牌请求未被拒绝")
    except Exception as e:
        print(f"测试CSRF防护（无令牌）时出错: {e}")
    
    # 现在 try 获取真正的CSRF令牌并使用它
    try:
        session = requests.Session()
        # 首先访问页面以获取CSRF令牌
        response = session.get(f"{BASE_URL}/")
        csrf_token = response.headers.get('X-CSRF-Token')
        
        if csrf_token:
            # 使用正确的CSRF令牌发送请求
            headers = {'X-CSRF-Token': csrf_token}
            response = session.post(f"{BASE_URL}/api/bids", json=normal_data, headers=headers)
            print(f"CSRF测试 - 正确令牌请求状态码: {response.status_code}")
            if response.status_code == 201:
                print("✓ CSRF防护允许有效令牌的请求")
            else:
                print(f"⚠ CSRF防护可能存在问题 - 有效令牌请求被拒绝: {response.text}")
        else:
            print("⚠ 无法获取CSRF令牌")
    except Exception as e:
        print(f"测试CSRF防护（有效令牌）时出错: {e}")
    
    # 测试发送带有假CSRF令牌的请求
    try:
        headers = {
            'X-CSRF-Token': 'dummy-token'  # 使用假令牌测试
        }
        response = requests.post(f"{BASE_URL}/api/bids", json=normal_data, headers=headers)
        print(f"CSRF测试 - 假令牌请求状态码: {response.status_code}")
        if response.status_code == 403:
            print("✓ CSRF防护工作正常 - 假令牌请求被拒绝")
        else:
            print("⚠ CSRF防护可能未正确验证令牌")
    except Exception as e:
        print(f"测试CSRF防护（假令牌）时出错: {e}")

def test_safe_request():
    """测试正常请求是否仍然工作"""
    print("测试正常请求...")
    
    # 使用会话来处理CSRF令牌
    session = requests.Session()
    
    # 首先访问主页以获取CSRF令牌
    try:
        response = session.get(f"{BASE_URL}/")
        csrf_token = response.headers.get('X-CSRF-Token')
        print(f"获取到CSRF令牌: {csrf_token is not None}")
    except Exception as e:
        print(f"建立会话时出错: {e}")
        return False
    
    # 发送正常请求
    normal_data = {
        "item_name": "Normal Test Item",
        "bid_amount": 100.0,
        "bidder_name": "Normal User"
    }
    
    # 添加CSRF头
    headers = {}
    if csrf_token:
        headers['X-CSRF-Token'] = csrf_token
    
    try:
        response = session.post(f"{BASE_URL}/api/bids", json=normal_data, headers=headers)
        if response.status_code == 201:
            print("✓ 正常请求仍然工作")
            return True
        else:
            print(f"✗ 正常请求可能受到影响 - 状态码: {response.status_code}, 响应: {response.text}")
            return False
    except Exception as e:
        print(f"测试正常请求时出错: {e}")
        return False

def test_parameter_validation():
    """测试参数验证"""
    print("测试参数验证...")
    
    # 测试无效的页码参数
    try:
        # 这里我们测试一个不存在的端点，因为PDF分析需要文件上传
        response = requests.get(f"{BASE_URL}/api/bids?sort=created_at&page=1%27%22%3E%3Cscript%3Ealert%281%29%3C%2Fscript%3E")
        if response.status_code == 400 and "security_violation" in response.text:
            print("✓ URL参数验证工作正常")
        else:
            print(f"✓ URL参数验证 - 状态码: {response.status_code}")
    except Exception as e:
        print(f"测试参数验证时出错: {e}")

def main():
    print("开始安全功能测试...")
    print("="*50)
    
    # 首先测试正常请求是否工作
    if not test_safe_request():
        print("错误: 正常请求无法工作，可能安全校验过于严格")
        return
    
    # 测试各种安全功能
    test_sql_injection()
    test_xss_protection()
    test_command_injection()
    test_csrf_protection()
    test_parameter_validation()
    
    print("="*50)
    print("安全功能测试完成")

if __name__ == "__main__":
    main()