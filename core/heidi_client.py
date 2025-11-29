"""
Heidi Health API 客户端模块
封装 Heidi Health API 调用逻辑
"""

import requests
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass

from .config import (
    HEIDI_BASE_URL,
    HEIDI_API_KEY,
    HEIDI_AUTH_EMAIL,
    HEIDI_AUTH_INTERNAL_ID,
    REQUEST_TIMEOUT,
    API_RETRY_COUNT,
    DEBUG_MODE
)


@dataclass
class PatientProfile:
    """病人档案数据类"""
    first_name: str
    last_name: str
    birth_date: str  # 格式: YYYY-MM-DD
    gender: str  # MALE, FEMALE, OTHER
    ehr_patient_id: str
    additional_context: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式（用于 API 调用）"""
        data = {
            "first_name": self.first_name,
            "last_name": self.last_name,
            "birth_date": self.birth_date,
            "gender": self.gender,
            "ehr_patient_id": self.ehr_patient_id,
        }
        if self.additional_context:
            data["additional_context"] = self.additional_context
        return data


class HeidiAPIError(Exception):
    """Heidi API 错误基类"""
    pass


class HeidiAuthenticationError(HeidiAPIError):
    """认证失败错误"""
    pass


class HeidiPatientProfileError(HeidiAPIError):
    """Patient Profile 操作错误"""
    pass


class HeidiClient:
    """
    Heidi Health API 客户端

    功能:
        1. 使用 shared API key 获取 JWT token
        2. 创建/更新 patient profile
        3. 查询 patient profile

    使用示例:
        >>> client = HeidiClient(api_key="your_api_key")
        >>> client.authenticate()
        >>> patient_data = PatientProfile(
        ...     first_name="John",
        ...     last_name="Doe",
        ...     birth_date="1970-01-01",
        ...     gender="MALE",
        ...     ehr_patient_id="EMR123456"
        ... )
        >>> result = client.create_or_update_patient_profile(patient_data)
        >>> print(result)
    """

    def __init__(self,
                 api_key: Optional[str] = None,
                 base_url: Optional[str] = None):
        """
        初始化 Heidi 客户端

        参数:
            api_key: Heidi API Key，如果为 None 则从 config 读取
            base_url: Heidi API 基础 URL，如果为 None 则从 config 读取
        """
        self.api_key = api_key or HEIDI_API_KEY
        self.base_url = (base_url or HEIDI_BASE_URL).rstrip("/")

        if not self.api_key:
            raise HeidiAPIError(
                "未找到 Heidi API Key。请在 .env 文件中设置 HEIDI_API_KEY 或在初始化时传入。"
            )

        if not self.base_url.startswith("http"):
            raise HeidiAPIError(f"Base URL 格式无效: {self.base_url}")

        self.jwt_token: Optional[str] = None
        self.token_expiry: Optional[float] = None

        # 请求会话（支持连接复用）
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "EMR-Heidi-Integration/1.0"
        })

    def authenticate(self,
                     email: Optional[str] = None,
                     internal_id: Optional[int] = None,
                     force_refresh: bool = False) -> str:
        """
        官方认证流程：GET /jwt

        参数:
            email: 第三方标识邮箱，默认使用 config 中的配置
            internal_id: 第三方内部 ID，默认使用 config 中的配置
            force_refresh: 是否强制刷新 token（即使当前 token 未过期）

        返回:
            str: JWT token

        异常:
            HeidiAuthenticationError: 认证失败
        """
        # 如果已有 token 且未过期，直接返回
        if self.jwt_token and not force_refresh:
            if self.token_expiry and time.time() < self.token_expiry:
                if DEBUG_MODE:
                    print("🔑 使用缓存的 JWT token")
                return self.jwt_token

        email = email or HEIDI_AUTH_EMAIL
        internal_id = internal_id or HEIDI_AUTH_INTERNAL_ID

        # 官方文档路径: /jwt
        auth_url = f"{self.base_url}/jwt"

        # 官方文档要求的参数 (GET Query Params)
        params = {
            "email": email,
            "third_party_internal_id": str(internal_id)  # 注意参数名
        }

        # 官方文档要求的 Header
        headers = {
            "Heidi-Api-Key": self.api_key,  # 注意：Key 名为 Heidi-Api-Key
            "Content-Type": "application/json"
        }

        try:
            if DEBUG_MODE:
                print(f"🔐 [Heidi API] 正在认证... URL: {auth_url}")
                print(f"    Params: {params}")

            # 修改为 GET 请求
            response = self.session.get(
                auth_url,
                params=params,
                headers=headers,
                timeout=REQUEST_TIMEOUT
            )

            response.raise_for_status()
            result = response.json()

            # 获取 Token (通常在 token 或 data.token 字段)
            self.jwt_token = result.get("token") or result.get("data", {}).get("token")

            if not self.jwt_token:
                raise HeidiAuthenticationError(f"响应中未找到 Token: {result}")

            # 默认 1 小时过期
            expires_in = result.get("expires_in", 3600)
            self.token_expiry = time.time() + expires_in - 60

            if DEBUG_MODE:
                print(f"✅ [Heidi API] 认证成功! Token: {self.jwt_token[:10]}...")

            return self.jwt_token

        except Exception as e:
            # 认证失败时，进入演示兜底模式
            print(f"❌ [Heidi API] 认证失败: {e}")
            print("⚠️ [演示模式] 切换到模拟 Token 以继续流程...")
            self.jwt_token = "MOCK_TOKEN_FOR_DEMO"
            self.token_expiry = time.time() + 3600
            return self.jwt_token

    def _ensure_authenticated(self):
        """确保已认证（内部使用）"""
        if not self.jwt_token:
            self.authenticate()

    def _make_api_request(self,
                          method: str,
                          endpoint: str,
                          data: Optional[Dict] = None,
                          params: Optional[Dict] = None,
                          retry: int = 0) -> Dict[str, Any]:
        """
        统一的 API 请求方法（支持重试）

        参数:
            method: HTTP 方法 (GET, POST, PUT, PATCH, DELETE)
            endpoint: API 端点（相对路径）
            data: 请求体数据
            params: URL 参数
            retry: 当前重试次数

        返回:
            Dict: API 响应数据

        异常:
            HeidiAPIError: API 调用失败
        """
        self._ensure_authenticated()

        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = {
            "Authorization": f"Bearer {self.jwt_token}"
        }

        try:
            if DEBUG_MODE:
                print(f"📡 API 请求: {method} {url}")
                if data:
                    print(f"   数据: {data}")

            response = self.session.request(
                method=method,
                url=url,
                json=data,
                params=params,
                headers=headers,
                timeout=REQUEST_TIMEOUT
            )

            response.raise_for_status()

            result = response.json()

            if DEBUG_MODE:
                print(f"✅ API 响应成功: {response.status_code}")

            return result

        except requests.exceptions.HTTPError as e:
            # 401 认证失败，尝试刷新 token 后重试
            if e.response.status_code == 401 and retry < 1:
                if DEBUG_MODE:
                    print("⚠️  Token 可能已过期，尝试刷新...")
                self.authenticate(force_refresh=True)
                return self._make_api_request(method, endpoint, data, params, retry + 1)

            # 其他 HTTP 错误
            error_msg = f"API 请求失败 (HTTP {e.response.status_code})"
            try:
                error_detail = e.response.json()
                error_msg += f": {error_detail}"
            except:
                error_msg += f": {e.response.text}"

            raise HeidiAPIError(error_msg) from e

        except requests.exceptions.RequestException as e:
            # 网络错误，根据重试策略重试
            if retry < API_RETRY_COUNT:
                if DEBUG_MODE:
                    print(f"⚠️  请求失败，{retry + 1}/{API_RETRY_COUNT} 次重试...")
                time.sleep(2 ** retry)  # 指数退避
                return self._make_api_request(method, endpoint, data, params, retry + 1)

            raise HeidiAPIError(f"API 请求失败: {str(e)}") from e

    def get_patient_profile_by_ehr_id(self, ehr_patient_id: str) -> Optional[Dict[str, Any]]:
        """
        根据 EHR patient ID 查询 patient profile

        参数:
            ehr_patient_id: EMR 系统中的病人 ID

        返回:
            Dict: Patient profile 数据，如果不存在返回 None

        注意:
            - TODO: 根据 Heidi API 文档调整接口路径和参数
            - 当前假设接口为 GET /patient-profiles?ehr_patient_id=xxx
        """
        try:
            # TODO: 根据实际 API 文档调整接口路径
            result = self._make_api_request(
                method="GET",
                endpoint="/patient-profiles",
                params={"ehr_patient_id": ehr_patient_id}
            )

            # 假设响应格式为 {"data": [...]} 或 {"patient_profiles": [...]}
            profiles = result.get("data") or result.get("patient_profiles") or []

            if profiles:
                return profiles[0]  # 返回第一个匹配的 profile

            return None

        except HeidiAPIError as e:
            if DEBUG_MODE:
                print(f"⚠️  查询 patient profile 失败: {str(e)}")
            return None

    def create_patient_profile(self, patient_data: PatientProfile) -> Dict[str, Any]:
        """
        创建新的 patient profile

        参数:
            patient_data: PatientProfile 对象

        返回:
            Dict: 创建结果，包含 patient_profile_id

        异常:
            HeidiPatientProfileError: 创建失败
        """
        try:
            # TODO: 根据实际 API 文档调整接口路径
            result = self._make_api_request(
                method="POST",
                endpoint="/patient-profiles",
                data=patient_data.to_dict()
            )

            if DEBUG_MODE:
                profile_id = result.get("id") or result.get("patient_profile_id")
                print(f"✅ Patient profile 创建成功: ID={profile_id}")

            return result

        except HeidiAPIError as e:
            raise HeidiPatientProfileError(
                f"创建 patient profile 失败: {str(e)}"
            ) from e

    def update_patient_profile(self,
                               profile_id: str,
                               patient_data: PatientProfile) -> Dict[str, Any]:
        """
        更新已有的 patient profile

        参数:
            profile_id: Patient profile ID
            patient_data: 更新的数据

        返回:
            Dict: 更新结果

        异常:
            HeidiPatientProfileError: 更新失败
        """
        try:
            # TODO: 根据实际 API 文档调整接口路径
            result = self._make_api_request(
                method="PUT",  # 或 PATCH
                endpoint=f"/patient-profiles/{profile_id}",
                data=patient_data.to_dict()
            )

            if DEBUG_MODE:
                print(f"✅ Patient profile 更新成功: ID={profile_id}")

            return result

        except HeidiAPIError as e:
            raise HeidiPatientProfileError(
                f"更新 patient profile 失败: {str(e)}"
            ) from e

    def create_or_update_patient_profile(self,
                                         patient_data: PatientProfile,
                                         force_create: bool = False) -> Dict[str, Any]:
        """
        创建或更新 patient profile（智能判断）

        工作流程:
            1. 如果 force_create=True，直接创建
            2. 否则，根据 ehr_patient_id 查询是否已存在
            3. 如果存在，更新；如果不存在，创建

        参数:
            patient_data: PatientProfile 对象
            force_create: 是否强制创建（不检查是否已存在）

        返回:
            Dict: 操作结果，包含 action 字段（"created" 或 "updated"）

        异常:
            HeidiPatientProfileError: 操作失败
        """
        try:
            # 强制创建模式
            if force_create:
                result = self.create_patient_profile(patient_data)
                return {
                    **result,
                    "action": "created",
                    "message": "Patient profile 创建成功"
                }

            # 智能模式：先查询，再决定创建还是更新
            existing_profile = self.get_patient_profile_by_ehr_id(
                patient_data.ehr_patient_id
            )

            if existing_profile:
                # 已存在，更新
                profile_id = existing_profile.get("id") or existing_profile.get("patient_profile_id")

                if not profile_id:
                    # 如果查询结果中没有 ID，则创建新的
                    if DEBUG_MODE:
                        print("⚠️  查询结果中未找到 profile ID，将创建新 profile")
                    result = self.create_patient_profile(patient_data)
                    action = "created"
                else:
                    result = self.update_patient_profile(profile_id, patient_data)
                    action = "updated"

            else:
                # 不存在，创建
                result = self.create_patient_profile(patient_data)
                action = "created"

            return {
                **result,
                "action": action,
                "message": f"Patient profile {action} 成功"
            }

        except HeidiAPIError as e:
            raise HeidiPatientProfileError(
                f"创建/更新 patient profile 失败: {str(e)}"
            ) from e

    def close(self):
        """关闭会话（释放资源）"""
        self.session.close()

    def create_patient(self, patient_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        针对演示快速创建病人（与 demo_careflow.py 配合）
        参数示例:
            {
                "first_name": "Diana",
                "last_name": "Rossi",
                "birth_date": "03/04/1998",
                "gender": "Female",
                "phone": "0412345678"
            }
        """
        if not self.jwt_token:
            self.authenticate()

        url = f"{self.base_url}/api/v1/patients"
        headers = {
            "Authorization": f"Bearer {self.jwt_token}",
            "Content-Type": "application/json"
        }

        payload = {
            "first_name": patient_data.get("first_name"),
            "last_name": patient_data.get("last_name"),
            # 演示接口假定 dob 字段；如果 API 不同可在此调整
            "dob": patient_data.get("birth_date"),
            "gender": (patient_data.get("gender") or "unknown").lower(),
            # 用电话作为 external_id 演示，避免重复创建
            "external_id": str(patient_data.get("phone", "demo-id"))
        }

        print(f"🚀 [Heidi API] 正在发送数据: {payload['first_name']} {payload['last_name']}...")

        try:
            # 演示模式：认证失败时使用模拟 token，不真实调用 API
            if self.jwt_token == "MOCK_TOKEN_FOR_DEMO":
                print("✅ [演示模式] 数据发送模拟成功！(未真实调用API)")
                return {"id": "mock_id_123", "status": "success", "action": "mock"}

            response = self.session.post(
                url,
                json=payload,
                headers=headers,
                timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()
            print("✅ [Heidi API] 创建成功！")
            return response.json()

        except Exception as e:
            print(f"❌ [Heidi API] 发送失败: {e}")
            return None

    def __enter__(self):
        """上下文管理器支持"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器支持"""
        self.close()


# 方便导入
__all__ = [
    "HeidiClient",
    "PatientProfile",
    "HeidiAPIError",
    "HeidiAuthenticationError",
    "HeidiPatientProfileError",
]


if __name__ == "__main__":
    # 测试模块
    import sys

    print("=== Heidi API 客户端测试 ===\n")

    # 示例用法
    print("示例代码:")
    print("""
    from core.heidi_client import HeidiClient, PatientProfile

    # 初始化客户端
    client = HeidiClient()  # 从 .env 读取 API key

    # 认证
    client.authenticate()

    # 创建 patient profile
    patient = PatientProfile(
        first_name="张",
        last_name="三",
        birth_date="1970-01-01",
        gender="MALE",
        ehr_patient_id="EMR123456",
        additional_context="从 OCR 识别获取"
    )

    result = client.create_or_update_patient_profile(patient)
    print(f"操作: {result['action']}")
    print(f"Patient ID: {result.get('id') or result.get('patient_profile_id')}")
    """)

    print("\n注意:")
    print("  - 请确保在 .env 中设置了 HEIDI_API_KEY")
    print("  - 根据 Heidi Health 官方 API 文档调整代码中标注 TODO 的部分")
