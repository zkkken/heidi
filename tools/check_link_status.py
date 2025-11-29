"""
诊断 Heidi 账号绑定状态：
1) 读取 .env 中的 HEIDI_API_KEY/HEIDI_BASE_URL/HEIDI_AUTH_EMAIL/HEIDI_AUTH_INTERNAL_ID
2) GET /jwt 获取 token（Header: Heidi-Api-Key, Params: email/third_party_internal_id）
3) GET /users/linked-account/access 检查绑定状态
"""

import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

# 让脚本能导入项目根目录的模块
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# 强制加载最新 .env
load_dotenv(override=True)


def check_status():
    api_key = os.getenv("HEIDI_API_KEY")
    base_url = os.getenv(
        "HEIDI_BASE_URL",
        "https://registrar.api.heidihealth.com/api/v2/ml-scribe/open-api",
    ).strip().rstrip("/")
    email = os.getenv("HEIDI_AUTH_EMAIL")
    internal_id = os.getenv("HEIDI_AUTH_INTERNAL_ID")

    print("=" * 50)
    print("🔍 Heidi 账号绑定状态诊断")
    print("=" * 50)
    print(f"配置文件: .env")
    print(f"API Key : ...{api_key[-4:] if api_key else 'None'}")
    print(f"Email   : {email}")
    print(f"Int ID  : {internal_id} (类型: {type(internal_id)})")
    print("-" * 50)

    # 1. 获取 token
    auth_url = f"{base_url}/jwt"
    headers = {"Heidi-Api-Key": api_key, "Content-Type": "application/json"}
    params = {"email": email, "third_party_internal_id": internal_id}

    print("📡 1. 正在获取 Token...")
    try:
        resp = requests.get(auth_url, headers=headers, params=params, timeout=15)
        resp.raise_for_status()
        token = resp.json().get("token")
        if not token:
            print(f"❌ Token 获取失败: 响应中无 token 字段，响应: {resp.text}")
            return
        print("✅ Token 获取成功")
    except Exception as e:
        print(f"❌ Token 获取失败: {e}")
        print("停止诊断。请检查 API Key/Email/Internal ID 是否正确，以及 HEIDI_BASE_URL 是否正确。")
        return

    # 2. 检查绑定状态
    print("📡 2. 查询绑定状态 (GET /users/linked-account/access)...")
    check_url = f"{base_url}/users/linked-account/access"
    check_headers = {"Authorization": f"Bearer {token}"}

    try:
        status_resp = requests.get(check_url, headers=check_headers, timeout=15)
        print(f"   HTTP 状态码: {status_resp.status_code}")

        data = status_resp.json()
        is_linked = data.get("is_linked", False)

        if is_linked:
            print("\n🎉 状态: 【已绑定 (LINKED)】")
            print(f"   关联的 Heidi ID: {data.get('account', {}).get('user_id')}")
            print("✅ 结论: 账号状态正常。")
        else:
            print("\n⚠️ 状态: 【未绑定 (NOT LINKED)】")
            print("❌ 结论: 这就是报错的原因！")
            print("   当前 Email+ID 组合没有关联到真实账号，请重新运行绑定脚本。")

    except Exception as e:
        print(f"❌ 查询请求失败: {e}")


if __name__ == "__main__":
    check_status()
