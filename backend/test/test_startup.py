"""
简化版安全测试
"""
import requests
import time

def test_app_startup():
    """测试应用是否能正常启动"""
    print("等待应用启动...")
    time.sleep(3)  # 等待应用启动
    
    try:
        response = requests.get("http://localhost:18080/")
        print(f"根路径访问成功，状态码: {response.status_code}")
        print(f"响应内容: {response.json()}")
        return True
    except Exception as e:
        print(f"访问失败: {e}")
        return False

if __name__ == "__main__":
    test_app_startup()