# Plant Doctor 阿里云 APK 打包与长期保存备用方案

> 这是 GitHub Actions 之外的备用方案，不替换当前已经验证成功的 GitHub 打包流程。推荐平时继续使用 GitHub Actions，并把成功的 APK 长期备份到阿里云 OSS；当 GitHub 无法构建或 Artifact 已过期时，再使用阿里云 ECS 重新打包。

## 1. 这套备用方案解决什么问题

GitHub Actions 的 `plantdoctor-apk` Artifact 只保留 14 天。14 天后删除的是该次构建产物，不是项目代码，仍然可以手动重新运行 GitHub workflow。

为了避免忘记下载或将来 GitHub 网络不稳定，增加两层后手：

1. **长期保存**：把每个已验收的 APK 上传到私有阿里云 OSS Bucket。
2. **独立重建**：准备一台阿里云 ECS Ubuntu 主机，在 ECS 上运行与 GitHub Actions 一致的 Buildozer 构建命令。

```text
GitHub/Gitee 代码  -->  阿里云 ECS 编译  -->  APK  -->  私有 OSS 长期保存
                                                               |
                                                               +--> 手机下载安装
```

## 2. 资源和费用提醒

这套方案会产生阿里云费用，包括 ECS 计算、系统盘、OSS 存储和公网流量。下单前以阿里云控制台的实时价格为准。

建议的 ECS 构建规格：

| 项目 | 建议 |
| --- | --- |
| 地域 | 选择离自己较近的中国内地地域 |
| 镜像 | Ubuntu 24.04 64 位 |
| CPU | 至少 4 核 |
| 内存 | 至少 8 GB，推荐 16 GB |
| 系统盘 | 至少 100 GB ESSD |
| CPU 架构 | x86_64/AMD64，不要选 ARM ECS |
| 公网 | 需要能下载 GitHub/Gitee、Android SDK、NDK、Gradle 和 Maven 依赖 |

Plant Doctor 会编译 NumPy、OpenCV、Kivy 和 Python Android 运行时。配置过低可能导致编译非常慢、内存不足或磁盘被占满。

官方控制台入口：

- [阿里云 ECS 控制台](https://ecs.console.aliyun.com/)
- [阿里云 OSS 控制台](https://oss.console.aliyun.com/)

## 3. 先建立 OSS 长期备份

### 3.1 创建私有 Bucket

1. 登录阿里云 OSS 控制台。
2. 创建一个 Bucket，例如 `plantdoctor-apk-backup`。Bucket 名需全球唯一，实际名称以控制台可用性为准。
3. 读写权限选择 **私有**，不要为了方便下载而设为公共读。
4. 服务器端加密可保持默认或选择 OSS 托管密钥。
5. 在 Bucket 内建立以下目录前缀：

```text
apk/
models/
checksums/
```

### 3.2 检查生命周期规则

进入 Bucket 的数据管理或生命周期配置，确认没有规则会在 14 天、30 天或其他期限后删除 `apk/` 和 `models/` 下的文件。

**OSS 签名下载链接过期，不等于 OSS 对象被删除。** 链接过期后只需要在控制台重新生成临时下载链接。

### 3.3 备份已经成功的 GitHub APK

GitHub Actions 打包成功后：

1. 下载 `plantdoctor-apk` ZIP。
2. 完整解压出 `.apk` 文件。
3. 用 Git 提交号重命名，例如 `PlantDoctor-1.0.0-4b7e583-debug-arm64.apk`。
4. 在 Windows PowerShell 计算校验值：

```powershell
Get-FileHash -Algorithm SHA256 C:\Users\21065\Downloads\PlantDoctor-1.0.0-4b7e583-debug-arm64.apk
```

5. 将 APK 上传到 OSS `apk/`。
6. 把文件名、SHA-256、Git 提交号、打包日期和测试手机记录成 TXT，上传到 `checksums/`。
7. 在手机完成一次安装和功能验收后，再将该版标记为“可演示版”。

## 4. `pest_model.pth` 的阿里云灾备

`ai_model/pest_model.pth` 仍然**不进入 APK**，也不要提交到 GitHub/Gitee。为防止电脑磁盘损坏，可以单独将它备份到私有 OSS `models/`。

上传前在 Windows 计算校验值：

```powershell
Get-FileHash -Algorithm SHA256 C:\Users\21065\Desktop\PlantDoctor\ai_model\pest_model.pth
Get-FileHash -Algorithm SHA256 C:\Users\21065\Desktop\PlantDoctor\ai_model\classes.json
```

建议备份为一个版本套件：

```text
models/convnext-181-2026-09/
├── pest_model.pth
├── classes.json
└── SHA256.txt
```

注意：

- Bucket 必须保持私有；
- 不要把 AccessKey、Bucket 密钥或长期签名 URL 写入 Git；
- 模型必须和配套的 `classes.json` 一起保存；
- 恢复后必须重新计算 SHA-256 并与记录比对；
- 模型下载回演示电脑后，放在 `PlantDoctor/ai_model/pest_model.pth`，不是放进手机。

## 5. 创建阿里云 ECS 备用构建机

### 5.1 创建实例

1. 打开 ECS 控制台并创建 Ubuntu 24.04 x86_64 实例。
2. 系统盘建议至少 100 GB。
3. 登录方式优先使用 SSH 密钥对，私钥只保存在自己的可信设备。
4. 安全组入方只放行自己当前公网 IP 到 TCP 22，不要将 SSH 向全网开放。
5. 构建完成后可停止实例节约计算费，但系统盘、弹性公网 IP 等资源仍可能计费。

**停止实例和释放实例不是一回事。** 释放 ECS 前必须确认 APK 已上传 OSS，需要的构建日志和校验值也已备份。

### 5.2 SSH 连接

在 Windows PowerShell 中：

```powershell
ssh -i C:\path\to\aliyun-ecs.pem <ECS用户名>@<ECS公网IP>
```

`<ECS用户名>` 以创建实例时的配置为准。连接后确认系统：

```bash
uname -m
cat /etc/os-release
df -h
free -h
```

`uname -m` 应显示 `x86_64`。

## 6. 在 ECS 安装打包环境

### 6.1 安装系统依赖

```bash
sudo apt-get update
sudo apt-get install -y \
  git zip unzip openjdk-17-jdk python3-pip python3-virtualenv \
  autoconf automake autopoint libtool pkg-config zlib1g-dev \
  libncurses5-dev libncursesw5-dev libtinfo6 cmake \
  libffi-dev libltdl-dev libssl-dev gettext build-essential \
  ccache curl tmux
```

检查 Java：

```bash
java -version
javac -version
```

两条命令都应显示 Java 17。

### 6.2 安装独立 Python 3.11 环境

当前成功的 GitHub workflow 使用 Python 3.11。为避免 Ubuntu 系统 Python 版本差异，ECS 使用 Miniconda 创建独立环境：

```bash
cd /tmp
curl -fLO https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh -b -p ~/miniconda3
source ~/miniconda3/bin/activate
conda create -n plantdoctor-build python=3.11 -y
conda activate plantdoctor-build
python -m pip install --upgrade pip setuptools wheel
python -m pip install "cython==0.29.34" "buildozer==1.5.0"
```

重新 SSH 登录后，需先执行：

```bash
source ~/miniconda3/bin/activate
conda activate plantdoctor-build
```

## 7. 将代码拉到 ECS

### 7.1 从 GitHub 拉取

```bash
cd ~
git clone https://github.com/hahahachaoge/PlantDoctor.git
cd ~/PlantDoctor
git checkout main
git pull --ff-only origin main
git rev-parse --short HEAD
```

记录 `git rev-parse --short HEAD` 的输出，这是该 APK 对应的代码版本。

### 7.2 GitHub 访问慢时使用 Gitee

只有在 Gitee `main` 已经和 GitHub `main` 同步的情况下才使用：

```bash
cd ~
git clone -b main https://gitee.com/im-convinced-11111/nongzhiyunjing.git PlantDoctor
cd ~/PlantDoctor
git rev-parse --short HEAD
```

不要只根据项目名判断代码是否最新，应比对 Git 提交号和需要演示的功能。

## 8. 在 ECS 打包 APK

### 8.1 检查当前配置

```bash
cd ~/PlantDoctor
grep -E '^(requirements|android.api|android.minapi|android.ndk|android.archs)' buildozer.spec
```

当前关键配置应包含：

```text
hostpython3==3.11.9
python3==3.11.9
kivy==2.3.1
android.api = 33
android.minapi = 24
android.ndk = 28c
android.archs = arm64-v8a
```

### 8.2 使用 tmux 打包

Android 首次构建时间较长。使用 tmux 可避免 SSH 断线导致命令中断：

```bash
tmux new -s plantdoctor-apk
source ~/miniconda3/bin/activate
conda activate plantdoctor-build
cd ~/PlantDoctor
set -o pipefail
buildozer -v android debug 2>&1 | tee buildozer.log
```

离开 tmux 但不停止构建：先按 `Ctrl+B`，松开后再按 `D`。

重新进入构建窗口：

```bash
tmux attach -t plantdoctor-apk
```

首次构建会下载 Android SDK、NDK 28c、Gradle 和大量 C/C++ 依赖。请保持 ECS 运行和网络稳定。不要在构建进行时释放、重启或更换 ECS。

### 8.3 检查构建结果

```bash
cd ~/PlantDoctor
ls -lh bin/*.apk
sha256sum bin/*.apk
```

`bin/` 中必须存在非空的 `.apk` 文件。记录：

- APK 文件名；
- APK 大小；
- SHA-256；
- `git rev-parse --short HEAD` 提交号；
- 构建日期；
- `buildozer.log` 是否有失败。

## 9. 从 ECS 下载 APK 到 Windows

先在 ECS 执行 `ls -lh ~/PlantDoctor/bin/*.apk` 得到确切文件名，再退出 SSH。在 Windows PowerShell 执行：

```powershell
scp -i C:\path\to\aliyun-ecs.pem "<ECS用户名>@<ECS公网IP>:/home/<ECS用户名>/PlantDoctor/bin/<APK文件名>" C:\Users\21065\Downloads\
```

PowerShell 中实际输入时，将尖括号占位符替换为真实值。也可以使用 ECS 控制台提供的文件管理/传输功能，以当前控制台界面为准。

下载后再次校验：

```powershell
Get-FileHash -Algorithm SHA256 C:\Users\21065\Downloads\<APK文件名>
```

该值必须与 ECS 上 `sha256sum` 的结果一致。

## 10. 将 ECS 构建的 APK 上传 OSS

最简单、不容易泄漏密钥的方式：

1. 先按上一节将 APK 下载到 Windows。
2. 登录 OSS 控制台。
3. 打开私有 Bucket 的 `apk/` 目录。
4. 上传 APK。
5. 将 SHA-256 和版本记录上传到 `checksums/`。
6. 从 OSS 再下载一次并校验，确认备份可用。

如果后续需要在 ECS 上自动上传，可使用阿里云 `ossutil`。应优先为 ECS 绑定最小权限的 RAM 角色，或使用专用 RAM 用户的最小 OSS 写入权限。不要使用主账号 AccessKey，不要将 AccessKey 写入脚本、Shell 历史或 Git 仓库。`ossutil` 的安装和登录命令应以阿里云当时的官方文档为准。

## 11. 从 OSS 下载并使用 APK

### 11.1 自己下载

1. 登录 OSS 控制台。
2. 进入 Bucket 的 `apk/` 目录。
3. 选择需要的 APK 版本。
4. 点击下载。
5. 在 Windows 使用 `Get-FileHash -Algorithm SHA256` 与 `checksums/` 中记录比对。

### 11.2 发给负责人

不要将 Bucket 改为公共读。在 OSS 控制台为指定 APK 生成有效期合理的临时签名 URL，或者自己下载后通过网盘、数据线、微信或 QQ 文件传输。

临时 URL 过期后，APK 仍然保存在 OSS，只需要重新生成链接。

### 11.3 手机安装

1. 将 `.apk` 下载到 Android 手机。
2. 允许当前浏览器或文件管理器“安装未知应用”。
3. 安装并允许相机、图片权限。
4. 如果存在签名不同的旧版，备份需要的本地数据后卸载旧版，再安装新版。
5. 启动电脑 FastAPI 服务，保证手机和电脑在同一局域网后测试识别。

## 12. 14 天后的具体恢复流程

### 情况 A：OSS 已有备份

1. 登录 OSS。
2. 在 `apk/` 找到最新的“可演示版”。
3. 下载并校验 SHA-256。
4. 传到手机安装。

该情况不需要重新打包。

### 情况 B：OSS 没有 APK，GitHub Artifact 已过期

优先打开 GitHub Actions，选择 **Build Android APK** 并手动运行 `main`。成功后立即下载并备份到 OSS。

### 情况 C：GitHub Actions 无法使用

1. 启动或创建阿里云 ECS。
2. 按本文档安装环境。
3. 从 GitHub 或已同步的 Gitee `main` 拉取代码。
4. 记录 Git 提交号。
5. 在 tmux 中执行 `buildozer -v android debug`。
6. 校验 ECS 上的 APK。
7. 下载到 Windows 并再次校验。
8. 上传到私有 OSS。
9. 安装到手机并进行完整功能验收。

## 13. 定期备份建议

每得到一个确认可用的 APK，当天完成以下操作：

- [ ] 文件名包含版本号和 Git 提交号；
- [ ] 记录 SHA-256；
- [ ] 上传 OSS `apk/`；
- [ ] 上传校验和版本记录到 `checksums/`；
- [ ] 从 OSS 试下载一次；
- [ ] 在真实手机安装并验收；
- [ ] 确认 OSS 生命周期不会自动删除；
- [ ] 确认 Bucket 仍为私有；
- [ ] 如果模型已更换，同步备份模型、`classes.json` 和 SHA-256。

## 14. 最重要的安全规则

1. 不把阿里云主账号 AccessKey 写入代码或文档。
2. 不把 SSH 私钥上传到 GitHub、Gitee 或 OSS 公共目录。
3. OSS Bucket 保持私有，分享时使用有限时间的签名 URL。
4. ECS SSH 端口只放行必要的来源 IP。
5. 释放 ECS 前一定确认 APK、校验值和必要日志已备份到 OSS。
6. 不盲目安装来历不明的“一键 APK 打包脚本”；保留当前已验证的 `buildozer.spec`、本地 NumPy recipe 和版本锁定。
