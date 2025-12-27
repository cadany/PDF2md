import requests
import time
import json

def test_app():
    print("Testing application connectivity...")
    try:
        # 等待应用启动
        time.sleep(2)
        
        # 测试根路径
        response = requests.get("http://localhost:18080/")
        print(f"Root endpoint status: {response.status_code}")
        print(f"Root endpoint response: {response.text[:200]}...")
        
        # 测试正常请求
        normal_data = {
            "item_name": "Test Item",
            "bid_amount": 100.0,
            "bidder_name": "Test User"
        }
        
        response = requests.post("http://localhost:18080/api/bids", json=normal_data)
        print(f"Normal request status: {response.status_code}")
        if response.status_code == 201:
            print("✓ Normal requests work correctly")
        else:
            print(f"Normal request response: {response.text}")
        
        # 测试SQL注入防护
        malicious_data = {
            "item_name": "Test'; DROP TABLE bids; --",
            "bid_amount": 100.0,
            "bidder_name": "Test User"
        }
        
        response = requests.post("http://localhost:18080/api/bids", json=malicious_data)
        print(f"SQL injection test status: {response.status_code}")
        if response.status_code == 400:
            print("✓ SQL injection protection works")
        else:
            print(f"SQL injection response: {response.text}")
        
        # 测试XSS防护
        xss_data = {
            "item_name": "<script>alert('XSS')</script>",
            "bid_amount": 100.0,
            "bidder_name": "Test User"
        }
        
        response = requests.post("http://localhost:18080/api/bids", json=xss_data)
        print(f"XSS test status: {response.status_code}")
        if response.status_code == 400:
            print("✓ XSS protection works")
        else:
            print(f"XSS response: {response.text}")
            
    except Exception as e:
        print(f"Error during testing: {e}")

if __name__ == "__main__":
    test_app()