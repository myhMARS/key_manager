# Key Manager

<p align="center">
  <img src="assets/icon/logo.png" alt="Key Manager Logo" width="120" />
</p>

<p align="center">
  <strong>跨平台 API Key 管理工具</strong> &mdash; 安全存储、余额查询、有效性校验，一站式管理你的 AI API Key。
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.12+-blue.svg" alt="Python 3.12+" />
  <img src="https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux%20%7C%20Android-brightgreen.svg" alt="Platform" />
  <img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License MIT" />
  <img src="https://img.shields.io/badge/Kivy-2.3+-purple.svg" alt="Kivy 2.3+" />
</p>

---

## 为什么需要 Key Manager

当你同时使用多个 AI 平台的 API 时，管理散落在各处的 Key 会变得很麻烦：

- 不记得某个 Key 还剩多少余额，想用时才发现余额不足
- Key 明文存储在笔记或环境变量里，安全性堪忧
- 换到新设备时，所有 Key 都要重新配置

Key Manager 用统一的界面管理所有 AI API Key，加密存储，一键查余额、验有效性，开箱即用。

## 功能特性

### 核心功能

- **Key 管理** &mdash; 添加、重命名、复制、删除 API Key，直观的卡片式导航
- **余额查询** &mdash; 一键查询已配置 Key 的剩余额度，自动适配不同平台的响应格式
- **Key 校验** &mdash; 通过平台 API 验证 Key 是否有效，添加后自动校验
- **自定义平台** &mdash; 支持任意 OpenAI 兼容接口的自定义平台，可编辑、可删除

### 安全

- **加密存储** &mdash; PBKDF2-HMAC-SHA256 派生密钥，HMAC-CTR + PKCS7 加密，HMAC-SHA256 防篡改
- **主密码保护** &mdash; 设置主密码解锁应用，切后台 60 秒自动锁定
- **生物认证** &mdash; Android 端支持指纹、面部识别、PIN 码快速解锁
- **纯标准库加密** &mdash; 加密模块零外部依赖，使用 hashlib、hmac、base64 标准库

### 内置平台

| 平台 | 余额查询 | Key 校验 |
|------|:---:|:---:|
| DeepSeek | &#10003; | &#10003; |
| Moonshot | &#10003; | &#10003; |
| OpenAI | &mdash; | &#10003; |
| 阿里百炼 | &mdash; | &#10003; |
| 小米 MiMo | &mdash; | &#10003; |

> OpenAI、阿里百炼、小米 MiMo 的 API 未公开余额查询端点，仅支持 Key 有效性校验。有余额查询需求的用户可通过自定义平台接入第三方代理接口。

自定义平台支持任意兼容 OpenAI API 格式的服务商。


<!--
| 首页 | 平台详情 | 锁屏 |
|:---:|:---:|:---:|
| ![Home](screenshots/home.png) | ![Platform](screenshots/platform.png) | ![Lock](screenshots/lock.png) |
-->

## 快速开始

### 环境要求

- Python 3.12+
- Android 构建需要 Linux 或 WSL（推荐 Ubuntu 22.04+）

### 安装与运行

```bash
# 克隆仓库
git clone https://github.com/myhMARS/key-manager.git
cd key-manager

# 安装依赖
pip install kivy httpx

# 或使用 uv（推荐）
uv sync

# 启动应用
python main.py
```

### 构建 Android APK

在 Linux / WSL 环境下：

```bash
# 安装 Buildozer 依赖
pip install buildozer

# 一键构建
buildozer android debug
```

构建产物位于 `bin/` 目录。APK 目标架构 arm64-v8a，最低 Android API 21。

首次构建建议先阅读 [Buildozer 快速入门](https://buildozer.readthedocs.io/en/latest/quickstart/) 安装系统依赖（SDK、NDK 等）。

## 项目结构

```
key-manager/
├── main.py                         # 应用入口
├── src/
│   └── key_manager/
│       ├── app_setup.py            # 字体注册、窗口尺寸初始化
│       ├── biometric.py            # Android 生物认证封装
│       ├── core/
│       │   ├── config.py           # 向后兼容导出
│       │   ├── crypto.py           # 加密模块（纯标准库实现）
│       │   ├── events.py           # 事件总线，模块间解耦通信
│       │   ├── platform_manager.py # 平台列表懒加载管理
│       │   ├── platforms.py        # 内置 + 自定义平台定义、余额解析器
│       │   ├── storage.py          # JSON 持久化存储与密码缓存
│       │   └── theme.py            # 平台颜色主题
│       └── ui/
│           ├── home_screen.py      # 首页卡片堆叠 + 滑动动画
│           ├── lock_screen.py      # 密码设置 / 解锁 / 生物认证
│           ├── platform_screen.py  # 平台详情、Key 列表、余额查询
│           ├── widgets.py          # 可复用组件
│           ├── popups.py           # 弹窗
│           └── kv/                 # Kivy 布局文件
├── assets/
│   ├── icon/                       # 平台图标 + 应用 Logo
│   ├── fonts/                      # Noto Sans SC 中文字体
│   └── presplash.png               # Android 启动屏
├── tests/
├── pyproject.toml                  # 项目元数据与依赖声明
├── buildozer.spec                  # Android 构建配置
└── README.md
```

## 数据存储

| 文件 / 位置 | 用途 |
|---|---|
| `~/.key_manager_config.json` | 加密后的 Key 和平台配置 |
| Android `SharedPreferences` | 生物认证密钥（设备绑定加密） |

加密方案：PBKDF2-HMAC-SHA256 (200,000 iterations) &#8594; 256 位密钥 &#8594; HMAC-CTR + PKCS7 加密 &#8594; HMAC-SHA256 完整性校验。

## 技术栈

| 层 | 技术 |
|---|---|
| UI 框架 | [Kivy](https://kivy.org/) 2.3+ |
| HTTP 客户端 | [httpx](https://www.python-httpx.org/) |
| 加密 | Python `hashlib` / `hmac` / `base64`（标准库） |
| Android 构建 | [Buildozer](https://buildozer.readthedocs.io/) |
| 包管理 | [uv](https://docs.astral.sh/uv/) / pip |

## 贡献指南

欢迎提交 Issue 和 Pull Request。

1. Fork 本仓库
2. 创建功能分支：`git checkout -b feat/amazing-feature`
3. 提交改动：`git commit -m 'feat: add amazing feature'`
4. 推送到分支：`git push origin feat/amazing-feature`
5. 提交 Pull Request

提交信息请遵循 [Conventional Commits](https://www.conventionalcommits.org/zh-hans/) 规范。

## 许可证

[MIT](LICENSE)

---

<p align="center">
  <sub>Made with Kivy, httpx, and Python standard library.</sub>
</p>