# tools/api_link_account.py
import sys
import os
import requests
import json
from pathlib import Path

# 添加项目根目录
sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def api_link_account():
    # 1. 配置信息
    api_key = os.getenv("HEIDI_API_KEY")
    # 确保 URL 格式正确，去除末尾斜杠
    base_url = os.getenv("HEIDI_BASE_URL", "https://registrar.api.heidihealth.com/api/v2/ml-scribe/open-api").strip().rstrip('/')
    
    email = os.getenv("HEIDI_AUTH_EMAIL")
    internal_id = os.getenv("HEIDI_AUTH_INTERNAL_ID")

    print(f"🔧 正在初始化 API 连接...")
    print(f"   Base URL: {base_url}")
    print(f"   Email: {email}")

    # 2. 获取 JWT Token (身份认证)
    jwt_url = f"{base_url}/jwt"
    headers = {
        "Heidi-Api-Key": api_key,
        "Content-Type": "application/json"
    }
    params = {
        "email": email,
        "third_party_internal_id": internal_id
    }

    try:
        # Step A: 获取 Token
        print(f"\n📡 [1/3] 正在获取 Access Token...")
        resp = requests.get(jwt_url, headers=headers, params=params)
        resp.raise_for_status()
        token = resp.json().get("token")
        
        if not token:
            print("❌ 获取 Token 失败")
            return

        print(f"✅ Token 获取成功")

        # Step B: 检查当前状态
        print(f"\n🔍 [2/3] 检查当前绑定状态...")
        status_url = f"{base_url}/users/linked-account/access"
        auth_headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        status_resp = requests.get(status_url, headers=auth_headers)
        if status_resp.status_code == 200:
            status_data = status_resp.json()
            is_linked = status_data.get("is_linked", False)
            if is_linked:
                print("🎉 恭喜！账号已经是【已绑定】状态。")
                print(f"   绑定信息: {status_data.get('account', {})}")
                return
            else:
                print("⚠️  当前状态: 【未绑定】")
        else:
            print(f"⚠️  状态检查失败 ({status_resp.status_code})，尝试强制绑定...")

        # Step C: 执行绑定
        print(f"\n🔗 [3/3] 准备进行绑定...")
        print("请在下方输入您的真实 Heidi 用户 ID (以 kp_ 开头)")
        real_user_id = input("请输入 kinde_user_id: ").strip()
        
        if not real_user_id.startswith("kp_"):
            print("❌ 格式错误：ID 通常以 'kp_' 开头")
            return

        link_url = f"{base_url}/users/linked-account"
        payload = {
            "kinde_user_id": real_user_id
        }
        
        link_resp = requests.post(link_url, headers=auth_headers, json=payload)
        
        if link_resp.status_code in [200, 201]:
            print("\n✅✅✅ 绑定成功！")
            print("您现在可以运行 RPA 流程了！")
            print(f"响应: {link_resp.json()}")
        elif link_resp.status_code == 409:
             # OpenAPIHeidiAccountAlreadyLinkedError
             print("\n✅ 绑定成功 (服务器提示已存在绑定关系)")
        else:
            print(f"\n❌ 绑定失败: {link_resp.status_code}")
            print(f"错误详情: {link_resp.text}")

    except Exception as e:
        print(f"\n❌ 发生异常: {e}")

if __name__ == "__main__":
    api_link_account()