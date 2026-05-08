# Key Manager

跨平台 API Key 管理工具，支持 Android 和桌面端。内置主流 AI 平台，可自定义扩展。

## 功能

- **Key 管理** — 添加、重命名、复制、删除 API Key
- **余额查询** — 支持 DeepSeek 余额查询，自动解析多种 API 响应格式
- **Key 校验** — 通过 API 端点验证 Key 有效性（OpenAI、百炼等）
- **自定义平台** — 添加任意 OpenAI 兼容接口的平台，支持编辑和删除
- **加密存储** — PBKDF2 派生密钥，HMAC-CTR 加密，HMAC 完整性校验
- **锁屏保护** — 主密码解锁，切后台自动锁定
- **生物认证** — Android 端支持指纹 / 面部 / PIN 码快速解锁
- **跨平台** — Android APK + Windows / macOS / Linux 桌面端

## 内置平台

| 平台 | 功能 |
|------|------|
| DeepSeek | 余额查询 |
| OpenAI | Key 校验 |
| 阿里百炼 | Key 校验 |
| 小米 Mimo | Key 管理 |

## 运行

```
# 安装依赖
pip install kivy httpx

# 或使用 uv
uv sync

python main.py
```

## 构建 Android APK

```
buildozer android debug
```

构建配置见 `buildozer.spec`，目标架构 arm64-v8a，最低 API 21。

## 项目结构

```
├── main.py                 # 应用入口，ScreenManager 导航，事件总线
├── app_setup.py            # 字体注册、窗口尺寸初始化
├── config.py               # 向后兼容导出（theme + platform_manager）
├── theme.py                # 平台颜色、色调工具函数
├── platforms.py            # 平台定义（内置 + 自定义加载）
├── platform_manager.py     # 懒加载平台列表管理
├── crypto.py               # 加密 / 解密模块（纯标准库）
├── storage.py              # JSON 持久化存储，密码缓存
├── biometric.py            # Android 生物认证封装
├── events.py               # 事件总线，解耦模块间通信
├── ui/
│   ├── lock_screen.py      # 密码设置 / 解锁 / 生物认证入口
│   ├── home_screen.py      # 首页卡片堆叠导航 + 滑动动画
│   ├── platform_screen.py  # 平台详情，Key 列表，余额查询
│   ├── widgets.py          # 可复用组件 (TouchCard, KeyItem, SnackBar)
│   ├── popups.py           # 弹窗 (AddKey, AddPlatform, EditPlatform, 确认删除)
│   └── kv/                 # Kivy 布局文件
├── assets/                 # 静态资源
│   ├── icon/               # 平台图标 + 应用 Logo
│   ├── fonts/              # 中文字体 (Noto Sans SC)
│   └── presplash.png       # Android 启动屏
├── pyproject.toml          # 项目依赖声明
└── buildozer.spec          # Android 构建配置
```

## 数据存储

- 配置文件: `~/.key_manager_config.json`
- Android 生物认证密钥: `SharedPreferences`（设备绑定加密）
- 加密方案: PBKDF2-HMAC-SHA256 (200k iterations) 派生 256 位密钥，HMAC-CTR + PKCS7 加密，HMAC-SHA256 完整性校验

## 技术栈

- **UI**: [Kivy](https://kivy.org/) 2.3+
- **网络**: [httpx](https://www.python-httpx.org/)
- **加密**: Python 标准库 (hashlib, hmac, base64)
- **构建**: [Buildozer](https://buildozer.readthedocs.io/)