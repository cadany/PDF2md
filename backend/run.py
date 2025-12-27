from flask import Flask
import os
import sys
import json
from dotenv import load_dotenv

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from routes.bid_routes import bid_bp
from routes.pdf_routes import pdf_bp

# 加载环境变量
load_dotenv()

app = Flask(__name__)

# 设置会话密钥（用于CSRF保护）
app.secret_key = os.environ.get('SECRET_KEY', 'fallback_secret_key_for_development')

# 注册蓝图
app.register_blueprint(bid_bp)
app.register_blueprint(pdf_bp)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 18080))
    app.run(debug=True, host='0.0.0.0', port=port)

    