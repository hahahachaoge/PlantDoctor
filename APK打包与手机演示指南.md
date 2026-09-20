# Plant Doctor APK 打包与手机演示指南

本文档用于将 Plant Doctor（智农慧眼）打包为可安装在 Android 手机上的 APK，并完成拍照识别、扫一扫、广州病虫害分布图等功能的现场演示。

## 1. 打包方案说明

本项目使用 Kivy 开发 Android 客户端，使用 Buildozer 和 python-for-android 生成 APK。

- Windows 不能直接使用 Buildozer 编译 Android APK，需要安装 WSL2，并在 Ubuntu 环境中构建。
- 用于内部演示时，生成 `debug APK` 即可，不需要应用商店签名。
- APK 只包含客户端，不包含约 335 MB 的 ConvNeXt 模型。
- 拍照识别时，手机需要通过局域网访问电脑上运行的 FastAPI 识别服务。
- 天气和广州地图需要访问互联网。

Buildozer 官方资料：

- [Buildozer 安装说明](https://buildozer.readthedocs.io/en/latest/installation/)
- [Buildozer Android 快速开始](https://buildozer.readthedocs.io/en/1.6.0/quickstart/)

## 2. 当前项目配置

项目已经提供 `buildozer.spec`，主要配置如下：

| 项目 | 当前配置 |
| --- | --- |
| 应用名称 | Plant Doctor |
| Android 包名 | `com.plantdoctor.plantdoctor` |
| 版本号 | `1.0.0` |
| Android 最低版本 | API 24（Android 7.0） |
| 目标 API | API 33 |
| NDK | 25b |
| 屏幕方向 | 竖屏 |
| CPU 架构 | `arm64-v8a`、`armeabi-v7a` |
| 权限 | 网络、相机、相册/图片读取 |
| 输出格式 | APK |

项目文件位置：

```text
C:\Users\21065\Desktop\PlantDoctor
```

## 3. 安装 WSL2 和 Ubuntu

当前电脑尚未安装 WSL。使用“管理员身份”打开 PowerShell，执行：

```powershell
wsl --install -d Ubuntu-24.04
```

安装结束后重启电脑，然后从开始菜单打开 Ubuntu。第一次启动时，按照提示设置 Linux 用户名和密码。

检查是否为 WSL2：

```powershell
wsl --list --verbose
```

正常情况下应看到类似内容：

```text
NAME            STATE           VERSION
Ubuntu-24.04    Running         2
```

如果显示 `VERSION 1`，执行：

```powershell
wsl --set-version Ubuntu-24.04 2
```

## 4. 安装 Android 打包依赖

以下命令全部在 Ubuntu 终端中执行。

### 4.1 安装系统依赖

```bash
sudo apt update

sudo apt install -y \
  git zip unzip openjdk-17-jdk python3-pip python3-virtualenv \
  autoconf libtool pkg-config zlib1g-dev \
  libncurses5-dev libncursesw5-dev libtinfo6 \
  cmake libffi-dev libssl-dev automake autopoint gettext
```

检查 Java：

```bash
java -version
javac -version
```

两条命令都应显示 Java 17。

### 4.2 安装 Rust

部分 Python/Android 依赖在编译时需要 Rust：

```bash
curl https://sh.rustup.rs -sSf | sh
```

安装界面出现选项时，直接按 Enter 使用默认配置，然后执行：

```bash
source "$HOME/.cargo/env"
```

### 4.3 创建独立 Python 环境

```bash
python3 -m virtualenv ~/plantdoctor-build-env
source ~/plantdoctor-build-env/bin/activate

python -m pip install --upgrade pip setuptools wheel
python -m pip install "cython==0.29.34"
python -m pip install git+https://github.com/kivy/buildozer
```

以后重新打开 Ubuntu 后，需要先执行：

```bash
source ~/plantdoctor-build-env/bin/activate
```

## 5. 将项目放入 WSL 文件系统

不要直接在 `/mnt/c/Users/21065/Desktop/PlantDoctor` 中构建。Buildozer 官方建议将项目放在 WSL 的 Linux 文件系统中，否则构建速度较慢，还可能出现权限、软链接或依赖识别错误。

推荐从 Gitee 的 `Front-end` 分支克隆：

```bash
cd ~
git clone -b Front-end https://gitee.com/im-convinced-11111/nongzhiyunjing.git PlantDoctor
cd ~/PlantDoctor
```

如果目录已经存在，需要更新代码：

```bash
cd ~/PlantDoctor
git pull
```

## 6. 配置识别服务器地址

### 6.1 为什么必须配置

手机中的 APK 不在电脑本机运行，因此不能使用 `127.0.0.1` 或 `localhost` 访问电脑服务。必须填写电脑在当前 Wi-Fi 下的局域网 IPv4 地址。

手机和电脑必须满足：

1. 连接同一个 Wi-Fi 或同一个手机热点；
2. 能够互相访问；
3. Windows 防火墙允许 Python 使用专用网络；
4. FastAPI 服务监听 `0.0.0.0:8000`。

### 6.2 查看电脑 IPv4

在 Windows PowerShell 中执行：

```powershell
ipconfig
```

找到“无线局域网适配器 WLAN”下面的 `IPv4 地址`。

局域网 IPv4 会随 Wi-Fi 或热点变化，正式演示当天必须重新确认，不要直接照抄其他环境的地址。

### 6.3 修改项目地址

打开 `config.py`，找到：

```python
API_BASE_URL = os.environ.get("PLANT_API_URL", "http://192.168.0.101:8000")
```

将默认地址替换为实际的电脑 IPv4。例如：

```python
API_BASE_URL = os.environ.get("PLANT_API_URL", "http://<电脑IPv4>:8000")
```

如果修改发生在 Windows 项目中，应先提交并推送，再到 WSL 项目中执行 `git pull`；也可以直接在 WSL 的 `~/PlantDoctor/config.py` 中修改后构建。

## 7. 构建 APK

进入项目并激活环境：

```bash
cd ~/PlantDoctor
source ~/plantdoctor-build-env/bin/activate
```

开始构建 debug APK：

```bash
buildozer -v android debug
```

注意事项：

- 第一次构建会自动下载 Android SDK、NDK、Gradle 和 Python/Android 依赖。
- 项目包含 NumPy 和 OpenCV，第一次构建可能耗时较长。
- 出现 Android SDK 许可证提示时输入 `y` 接受。
- 构建期间保持网络连接，不要关闭 Ubuntu 窗口。
- 后续再次构建会复用下载缓存，速度通常会更快。

构建成功后查看 APK：

```bash
ls -lh ~/PlantDoctor/bin/*.apk
```

实际文件名由 Buildozer 生成，一般包含应用名、版本号、CPU 架构和 `debug` 字样。

## 8. 将 APK 复制到 Windows

在 Ubuntu 中执行：

```bash
cp ~/PlantDoctor/bin/*.apk /mnt/c/Users/21065/Desktop/
```

复制完成后，Windows 桌面上会出现 APK 文件。

可以通过以下方式传给负责人：

- 数据线复制；
- 微信或 QQ 文件传输；
- 局域网文件传输；
- 上传到网盘后下载。

## 9. 手机安装 APK

1. 在手机上打开 APK 文件。
2. 如果系统拦截，进入设置允许当前文件管理器或聊天软件“安装未知应用”。
3. 重新点击 APK 并安装。
4. 首次打开应用时，允许相机和照片访问权限。

如果手机已经安装过同包名、但签名不同的旧版本，应先卸载旧版本再安装。

## 10. 启动电脑识别服务

APK 安装成功不代表拍照识别服务已经启动。演示识别前，需要在 Windows 项目目录运行 FastAPI 服务。

打开 PowerShell：

```powershell
cd C:\Users\21065\Desktop\PlantDoctor
python -m uvicorn ai_model.api:app --host 0.0.0.0 --port 8000
```

保持该 PowerShell 窗口开启。

首次启动时，如果 Windows 防火墙询问是否允许访问，请勾选“专用网络”并允许。

## 11. 演示前连接测试

在手机浏览器输入：

```text
http://电脑IPv4:8000
```

例如：

```text
http://<电脑IPv4>:8000
```

能够看到 API 启动信息，说明手机到电脑的网络已经连通。之后再打开 Plant Doctor APK 测试拍照识别。

如果浏览器访问失败，应依次检查：

1. 手机和电脑是否连接同一个网络；
2. 电脑 IPv4 是否发生变化；
3. FastAPI 服务是否正在运行；
4. 服务启动命令是否包含 `--host 0.0.0.0`；
5. Windows 防火墙是否拦截 8000 端口；
6. 当前 Wi-Fi 是否启用了客户端隔离。

## 12. 建议的现场演示流程

### 12.1 演示前准备

- 电脑和手机连接同一个稳定 Wi-Fi；
- 电脑接通电源；
- 提前启动 FastAPI 服务；
- 手机浏览器确认能访问 `http://电脑IPv4:8000`；
- 打开 APK 并提前授予相机、相册权限；
- 准备两到三张清晰的作物病害图片；
- 保留一张健康叶片图片用于对比；
- 确认广州地图可以正常加载；
- 避免演示时电脑进入睡眠或切换网络。

### 12.2 推荐演示顺序

1. 登录普通用户或 VIP 用户；
2. 展示首页天气、搜索和常用功能；
3. 使用相册图片或相机完成病虫害识别；
4. 展示识别名称、置信度、别名、分布地区、形态特征和 Top-5；
5. 搜索一个关键词，展示多条结果和详情返回逻辑；
6. 打开广州病虫害分布图，演示自由拖动和分布数据；
7. 展示扫一扫、用户专属二维码和通讯录；
8. 展示我的档案、通知、订单、反馈和客服页面。

## 13. 常见问题

### 13.1 `wsl` 提示未安装

使用管理员 PowerShell 执行：

```powershell
wsl --install -d Ubuntu-24.04
```

然后重启电脑。

### 13.2 Buildozer 下载失败

通常是 GitHub、Google Android SDK 或 Maven 网络连接问题。可以：

- 换用稳定网络；
- 检查 WSL 是否能访问 GitHub；
- 配置可用的 HTTP/HTTPS 代理；
- 重新执行 `buildozer -v android debug`，已下载内容通常会继续使用。

### 13.3 构建卡在许可证界面

在终端输入 `y` 并按 Enter，接受 Android SDK 许可证。

### 13.4 找不到 APK

执行：

```bash
find ~/PlantDoctor/bin -maxdepth 1 -name "*.apk" -ls
```

如果没有结果，应查看构建日志最后出现的 `error` 或 `failed` 信息。

### 13.5 手机提示“应用未安装”

可能原因：

- 已安装同包名但签名不同的旧版，应先卸载旧版；
- 手机 CPU 不支持 APK 架构；
- APK 在传输过程中损坏；
- 手机存储空间不足；
- 系统禁止安装未知来源应用。

### 13.6 应用能打开，但拍照识别失败

优先检查服务器地址。APK 中写入的电脑 IPv4 必须与演示现场电脑的实际 IPv4 一致。还需要确认手机和电脑处于同一网络、FastAPI 正在运行并且防火墙已放行。

### 13.7 地图空白或加载缓慢

广州地图使用在线地图瓦片。检查手机是否能访问互联网，首次进入时等待瓦片下载完成；已经访问过的区域会使用本地缓存。

### 13.8 查看 Android 运行日志

如果已经在 Windows 安装 Android Platform Tools，并通过 USB 连接手机，可以执行：

```powershell
adb devices
adb logcat | Select-String "python|PythonActivity"
```

手机需要开启开发者选项和 USB 调试。

## 14. 可选：缩短首次构建时间

当前 `buildozer.spec` 同时构建 64 位和 32 位 APK：

```ini
android.archs = arm64-v8a, armeabi-v7a
```

如果负责人使用近年的 64 位 Android 手机，可以临时改为：

```ini
android.archs = arm64-v8a
```

这样可以减少 OpenCV 等原生依赖的编译量。若不确定手机架构，保留当前双架构配置更稳妥。

## 15. 最终验收清单

- [ ] WSL2 和 Ubuntu 已安装；
- [ ] Java 17、Buildozer、Cython 和系统依赖已安装；
- [ ] 项目位于 `~/PlantDoctor`，而不是直接在 `/mnt/c` 中构建；
- [ ] `config.py` 中的服务器 IPv4 与演示现场一致；
- [ ] `buildozer -v android debug` 执行成功；
- [ ] `bin/` 目录存在 APK；
- [ ] APK 已复制到 Windows 并能在手机安装；
- [ ] 手机与电脑处于同一网络；
- [ ] FastAPI 服务监听 `0.0.0.0:8000`；
- [ ] 手机浏览器可以访问识别 API；
- [ ] 拍照、相册、识别、扫一扫、地图和返回导航均已实机测试。
