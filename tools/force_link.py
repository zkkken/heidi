# tools/force_link.py
import sys
import os
import requests
from pathlib import Path

# 添加项目路径以读取配置
sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv

load_dotenv()

def force_link():
    # 1. 准备配置
    api_key = os.getenv("HEIDI_API_KEY")
    base_url = os.getenv("HEIDI_BASE_URL", "https://registrar.api.heidihealth.com/api/v2/ml-scribe/open-api").strip().rstrip('/')
    email = os.getenv("HEIDI_AUTH_EMAIL")
    internal_id = os.getenv("HEIDI_AUTH_INTERNAL_ID")

    # ★★★ 这里填入您之前找到的真实 ID ★★★
    REAL_USER_ID = "kp_5fafa82a9a1c4a80baacaaa0f8a4a8c"

    print(f"🚀 开始强制绑定...")
    print(f"   API Key: ...{api_key[-4:]}")
    print(f"   Target User ID: {REAL_USER_ID}")

    # 2. 获取 Token
    try:
        jwt_resp = requests.get(
            f"{base_url}/jwt",
            headers={"Heidi-Api-Key": api_key, "Content-Type": "application/json"},
            params={"email": email, "third_party_internal_id": internal_id}
        )
        jwt_resp.raise_for_status()
        token = jwt_resp.json().get("token")
        print("✅ Token 获取成功")
    except Exception as e:
        print(f"❌ Token 获取失败: {e}")
        return

    # 3. 发送绑定请求
    link_url = f"{base_url}/users/linked-account"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    payload = {"kinde_user_id": REAL_USER_ID}

    print(f"🔗 正在请求绑定接口...")
    try:
        resp = requests.post(link_url, headers=headers, json=payload)

        if resp.status_code in [200, 201]:
            print("\n🎉🎉🎉 绑定成功！")
            print("账号关联已建立。现在 API 有权限创建病人了。")
        elif resp.status_code == 409:
            print("\n✅ 绑定已存在 (无需重复绑定)。")
        else:
            print(f"\n❌ 绑定失败: {resp.status_code}")
            print(f"响应: {resp.text}")

    except Exception as e:
        print(f"❌ 请求异常: {e}")

if __name__ == "__main__":
    force_link()
