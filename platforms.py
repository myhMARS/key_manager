from dataclasses import dataclass


@dataclass
class Platform:
    id: str
    name: str
    icon: str
    base_url: str = ""
    balance_url: str = ""
    balance_parser: str = ""
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
        icon_path="icon/deepseek.png",
        base_url="https://api.deepseek.com",
        balance_url="/user/balance",
        balance_parser="deepseek",
        key_prefix="sk-",
    ),
    "openai": Platform(
        id="openai",
        name="OpenAI",
        icon="O",
        icon_path="icon/openai.png",
        base_url="https://api.openai.com",
        verify_url="/v1/models",
        key_prefix="sk-",
    ),
    "bailian": Platform(
        id="bailian",
        name="阿里百炼",
        icon="A",
        icon_path="icon/bailian.png",
        base_url="https://dashscope.aliyuncs.com/compatible-mode",
        verify_url="/v1/models",
        key_prefix="sk-",
    ),
    "mimo": Platform(
        id="mimo",
        name="小米 Mimo",
        icon="M",
        icon_path="icon/xiaomi.png",
        base_url="https://api.xiaomimimo.com",
        verify_url="/v1/models",
    ),
}

# Combined platforms dict (built-in + custom)
PLATFORMS: dict[str, Platform] = dict(BUILTIN_PLATFORMS)


def load_custom_platforms():
    """Load custom platforms from storage and merge into PLATFORMS.
    Clears previous custom entries first to avoid duplicates."""
    import storage

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
