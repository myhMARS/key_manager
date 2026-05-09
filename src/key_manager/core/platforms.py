from dataclasses import dataclass


# ---------------------------------------------------------------------------
#  Balance response parsers — each returns [(label, value), ...]
# ---------------------------------------------------------------------------

def parse_deepseek_balance(data: dict) -> list:
    """DeepSeek format: {"is_available": true, "balance_infos": [...]}"""
    if not data.get("is_available"):
        return []
    entries = []
    for info in data.get("balance_infos", []):
        for k, v in info.items():
            entries.append((k.replace("_", " ").title(), str(v)))
    return entries


def parse_moonshot_balance(data: dict) -> list:
    """Moonshot format: {"code": 0, "data": {...}, "status": true}"""
    balance_data = data.get("data", {})
    if not isinstance(balance_data, dict):
        return []
    return [
        (k.replace("_", " ").title(), str(v))
        for k, v in balance_data.items()
        if isinstance(v, (int, float, str))
    ]


def parse_generic_balance(data: dict) -> list:
    """Fallback: extract numeric/string values from top-level or one level of nesting."""
    entries = []
    for k, v in data.items():
        if isinstance(v, (int, float, str)):
            entries.append((k.replace("_", " ").title(), str(v)))
        elif isinstance(v, dict):
            for sub_k, sub_v in v.items():
                if isinstance(sub_v, (int, float, str)):
                    entries.append((sub_k.replace("_", " ").title(), str(sub_v)))
        elif isinstance(v, list) and v and isinstance(v[0], dict):
            for item in v:
                for sub_k, sub_v in item.items():
                    if isinstance(sub_v, (int, float, str)):
                        entries.append((sub_k.replace("_", " ").title(), str(sub_v)))
    return entries


# Platform-id → parser function
BALANCE_PARSERS = {
    "deepseek": parse_deepseek_balance,
    "moonshot": parse_moonshot_balance,
}


def get_balance_parser(platform_id: str):
    """Return the balance parser for *platform_id*, or the generic fallback."""
    return BALANCE_PARSERS.get(platform_id, parse_generic_balance)


@dataclass
class Platform:
    id: str
    name: str
    icon: str
    base_url: str = ""
    balance_url: str = ""
    verify_url: str = ""
    auth_header: str = "Bearer {api_key}"
    key_prefix: str = ""
    icon_path: str = ""
    is_custom: bool = False


# Built-in platforms
BUILTIN_PLATFORMS: dict[str, Platform] = {
    "deepseek": Platform(
        id="deepseek",
        name="DeepSeek",
        icon="D",
        icon_path="assets/icon/deepseek.png",
        base_url="https://api.deepseek.com",
        balance_url="/user/balance",
        key_prefix="sk-",
    ),
    "openai": Platform(
        id="openai",
        name="OpenAI",
        icon="O",
        icon_path="assets/icon/openai.png",
        base_url="https://api.openai.com",
        verify_url="/v1/models",
        key_prefix="sk-",
    ),
    "bailian": Platform(
        id="bailian",
        name="阿里百炼",
        icon="A",
        icon_path="assets/icon/bailian.png",
        base_url="https://dashscope.aliyuncs.com/compatible-mode",
        verify_url="/v1/models",
        key_prefix="sk-",
    ),
    "mimo": Platform(
        id="mimo",
        name="小米 Mimo",
        icon="M",
        icon_path="assets/icon/xiaomi.png",
        base_url="https://api.xiaomimimo.com",
        verify_url="/v1/models",
    ),
    "moonshot": Platform(
        id="moonshot",
        name="Moonshot",
        icon="M",
        icon_path="assets/icon/moonshot.png",
        base_url="https://api.moonshot.cn",
        balance_url="/v1/users/me/balance",
        key_prefix="sk-",
    ),
}

# Combined platforms dict (built-in + custom)
PLATFORMS: dict[str, Platform] = dict(BUILTIN_PLATFORMS)


def load_custom_platforms():
    """Load custom platforms from storage and merge into PLATFORMS.
    Clears previous custom entries first to avoid duplicates."""
    from . import storage

    # Remove old custom platforms
    to_remove = [pid for pid, p in PLATFORMS.items() if p.is_custom]
    for pid in to_remove:
        del PLATFORMS[pid]

    # Load fresh from storage
    customs = storage.get_custom_platforms()
    for p in customs:
        plat = Platform(
            id=p["id"],
            name=p["name"],
            icon=p["name"][0].upper() if p["name"] else "?",
            base_url=p.get("base_url", ""),
            verify_url=p.get("verify_url", ""),
            balance_url=p.get("balance_url", ""),
            auth_header=p.get("auth_header", "Bearer {api_key}"),
            is_custom=True,
        )
        PLATFORMS[plat.id] = plat


def get_platform(platform_id: str) -> Platform | None:
    return PLATFORMS.get(platform_id)


def get_platform_list() -> list:
    """Return ordered list of all platforms."""
    return list(PLATFORMS.values())
