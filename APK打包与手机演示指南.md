# Plant Doctor APK 打包、下载与手机演示指南

> 本文档与当前仓库的实际配置保持一致。当前采用 **GitHub Actions 云端打包**，不需要在 Windows 上安装 WSL、Ubuntu、Android SDK 或 Buildozer。

GitHub Artifact 过期、GitHub 无法构建或需要长期保存 APK 时，参见 [阿里云 APK 打包与长期保存备用方案](./阿里云APK打包与长期保存备用方案.md)。

## 1. 先理解整体结构

Plant Doctor 在手机上演示时分为两部分：

1. **Android 客户端 APK**：安装在手机上，负责界面、拍照、选图、显示识别结果、地图等功能。
2. **电脑识别服务**：在电脑上运行 `ai_model/api.py`，使用 `pest_model.pth` 完成真正的病虫害识别。

手机与电脑需连接同一个 Wi-Fi 或同一个手机热点。APK 会把照片发给电脑的 FastAPI 服务，再显示服务端返回的 Top-5、置信度、别名、分布地区和防治信息。

```text
手机 APK  --局域网-->  电脑 FastAPI  -->  ai_model/pest_model.pth
```

## 2. 当前已验证的打包配置

| 项目 | 当前值 |
| --- | --- |
| 工作流 | `.github/workflows/build.yml` |
| 触发方式 | 推送到 GitHub `main` 或手动运行 workflow |
| 云端系统 | Ubuntu 24.04 |
| Python | 3.11 |
| Buildozer | 1.5.0 |
| Kivy | 2.3.1 |
| Android NDK | 28c |
| Android 目标 API | 33 |
| Android 最低 API | 24（Android 7.0） |
| CPU 架构 | `arm64-v8a` |
| 包名 | `com.plantdoctor.plantdoctor` |
| 产物名 | `plantdoctor-apk` |
| 产物保留时间 | 14 天 |

2026-09-20 已实际打包成功的运行：[Build Android APK #35512263711](https://github.com/hahahachaoge/PlantDoctor/actions/runs/35512263711)。该链接只是成功示例，以后应下载自己最新提交对应的构建产物。

## 3. `pest_model.pth` 怎么处理

### 3.1 不要把模型提交到 GitHub

当前模型位置是：

```text
C:\Users\21065\Desktop\PlantDoctor\ai_model\pest_model.pth
```

当前文件大约 351 MB。GitHub 普通 Git 仓库不适合直接提交这么大的权重文件，项目的 `.gitignore` 已经忽略：

```gitignore
*.pth
pest_model.pth
best_model.zip
```

因此：

- `git add .` 不会把模型上传到 GitHub；
- GitHub Actions 打包时也不需要该模型；
- `buildozer.spec` 排除了 `ai_model` 目录，模型不会被塞入 APK；
- 模型只需保留在运行识别服务的电脑上。

### 3.2 模型必须放在哪里

FastAPI 启动时固定读取：

```text
PlantDoctor/
└── ai_model/
    ├── api.py
    ├── pest_model.pth
    ├── classes.json
    ├── disease_info.json
    └── disease_metadata.json
```

文件名必须是 `pest_model.pth`。如果拿到的是 `best_model.zip`，先解压，找到真正的 `.pth` 权重文件，确认是本项目对应的 181 类 ConvNeXt-Base 模型后，将它放到 `ai_model` 并命名为 `pest_model.pth`。不要仅把 ZIP 放在项目根目录。

检查模型是否存在：

```powershell
Get-Item C:\Users\21065\Desktop\PlantDoctor\ai_model\pest_model.pth
```

### 3.3 更换模型后是否要重新打 APK

**不需要。** `pest_model.pth` 在电脑服务端，不在 APK 内。更换模型后只需要：

1. 停止正在运行的 FastAPI；
2. 备份旧的 `ai_model/pest_model.pth`；
3. 放入新模型，仍命名为 `pest_model.pth`；
4. 确认 `classes.json` 的类别数量和顺序与新模型一致；
5. 重新启动 FastAPI。

如果新模型的类别数、类别顺序或网络结构不同，不能只改文件名，还必须同步修改 `classes.json` 和 `ai_model/api.py`。

## 4. 打包前必须检查

### 4.1 确认服务器 IP

手机不能用 `127.0.0.1` 访问电脑。在 Windows PowerShell 执行：

```powershell
ipconfig
```

找到当前 Wi-Fi 网卡的 IPv4，例如 `192.168.0.101`。然后检查 `config.py`：

```python
API_BASE_URL = os.environ.get("PLANT_API_URL", "http://192.168.0.101:8000")
```

当前服务端没有内置 UDP 广播，所以不要完全依赖自动发现。演示环境的电脑 IP 如果变了，最稳妥的方法是修改 `config.py`、提交后重新打包。

### 4.2 确认本地代码正常

```powershell
cd C:\Users\21065\Desktop\PlantDoctor
git status
git branch --show-current
```

应确认自己正在 `main` 分支，并检查本地改动是否都应该提交。不要把个人数据库、临时照片、模型权重或密码提交到仓库。

## 5. 使用 GitHub Actions 打包 APK

### 5.1 方法一：提交代码后自动打包

当代码推送到 GitHub `main` 分支时，`.github/workflows/build.yml` 会自动启动。

```powershell
cd C:\Users\21065\Desktop\PlantDoctor
git add <需要提交的文件>
git commit -m "feat: 更新 Android 演示功能"
git push origin main
```

推送完成后打开：

```text
https://github.com/hahahachaoge/PlantDoctor/actions
```

点开最新的 **Build Android APK** 运行。黄色表示正在运行，绿色表示成功，红色表示失败。首次或无缓存构建可能需要 20–35 分钟。

### 5.2 方法二：不改代码，手动重新打包

1. 打开 GitHub 仓库的 **Actions** 页面。
2. 左侧选择 **Build Android APK**。
3. 点击右侧 **Run workflow**。
4. 分支选择 `main`。
5. 再点击绿色 **Run workflow** 确认。

该方法只是重新打包 GitHub 上现有的 `main` 代码，不会包含尚未推送的本地修改。

## 6. 打包成功后如何下载 APK

### 6.1 从 GitHub 网页下载

1. 打开 [GitHub Actions 页面](https://github.com/hahahachaoge/PlantDoctor/actions)。
2. 点开最新且显示绿色对勾的 **Build Android APK**。
3. 滚动到页面底部的 **Artifacts**。
4. 点击 `plantdoctor-apk`。
5. GitHub 会下载一个 ZIP 压缩包。
6. 将 ZIP 完整解压，在其中找到 `.apk` 文件。

Artifact 会在 14 天后过期。过期后不需要修改代码，在 Actions 页面手动重新运行 workflow 即可生成新的下载产物。

### 6.2 下载速度慢怎么办

GitHub Artifact 会跳转到 GitHub 的对象存储节点。某些网络环境下下载可能很慢，关闭 VPN 也不一定更快。可按以下顺序尝试：

1. 用 Chrome 或 Edge 登录 GitHub 后直接下载；
2. 切换到其他宽带或手机热点；
3. 在网络较好的电脑上下载，再通过网盘或数据线传输；
4. 下载中断时优先使用支持断点续传的浏览器或下载工具。

不要将尚未完成的 `.crdownload` 或部分 ZIP 改名为 APK。

## 7. 下载后如何传到手机

可选任意一种方式：

- USB 数据线复制到手机 `Download` 目录；
- 微信或 QQ 的文件传输；
- 网盘上传后在手机下载；
- 局域网文件传输工具。

发送的是解压后的 `.apk` 文件，不是 `plantdoctor-apk.zip`。

## 8. 手机如何安装 APK

1. 在手机文件管理器中点击 APK。
2. 如果系统阻止，按提示允许当前浏览器、文件管理器、微信或 QQ“安装未知应用”。
3. 返回再次点击安装。
4. 首次启动后允许相机和图片访问权限。

当前 APK 只包含 `arm64-v8a`，适用于大多数近年的 64 位 Android 手机。如果手机提示不兼容，需先确认其 CPU 是否支持 ARM64。

如果提示“应用未安装”，常见原因是手机已有同包名但签名不同的旧版。先备份需要的本地数据，卸载旧版，再安装新 APK。卸载会删除该应用在手机上的本地数据。

## 9. 启动电脑端识别服务

### 9.1 首次安装服务端依赖

APK 的 `requirements.txt` 不包含 PyTorch 服务端依赖。在 Windows PowerShell 中执行：

```powershell
cd C:\Users\21065\Desktop\PlantDoctor
python -m pip install torch torchvision fastapi "uvicorn[standard]" pillow python-multipart requests
```

### 9.2 检查必需文件

```powershell
Test-Path .\ai_model\pest_model.pth
Test-Path .\ai_model\classes.json
Test-Path .\ai_model\disease_info.json
Test-Path .\ai_model\disease_metadata.json
```

上述命令应返回 `True`。`api.py` 在缺少模型或类别文件时会直接报错停止。

### 9.3 启动 API

```powershell
cd C:\Users\21065\Desktop\PlantDoctor
python -m uvicorn ai_model.api:app --host 0.0.0.0 --port 8000
```

看到以下关键信息表示启动成功：

```text
模型加载成功，可识别 181 类病虫害
Uvicorn running on http://0.0.0.0:8000
```

不要关闭该 PowerShell 窗口。Windows 防火墙首次询问时，允许 Python 访问**专用网络**。

## 10. 安装后必须进行的联调测试

1. 让手机和电脑连接同一 Wi-Fi 或热点。
2. 电脑上保持 FastAPI 运行。
3. 在手机浏览器访问 `http://<电脑IPv4>:8000`。
4. 如果看到 `{"message":"病虫害识别 API 已启动"}`，说明局域网已打通。
5. 打开 APK，先用相册图片识别，再测试拍照识别。
6. 检查主结果、Top-5、置信度、别名、分布地区和防治信息是否正常。

如果手机浏览器都无法访问 API，先不要反复重装 APK，应检查：

- 手机和电脑是否在同一局域网；
- `config.py` 中的 IP 是否为当前电脑 IPv4；
- FastAPI 是否使用 `--host 0.0.0.0 --port 8000` 启动；
- Windows 防火墙是否拦截 Python 或 TCP 8000 端口；
- Wi-Fi 是否启用了 AP/客户端隔离；
- 电脑 IP 是否因换 Wi-Fi 而变化。

## 11. APK 更新后应该怎么做

每次修改手机端代码后：

1. 把修改提交并推送到 GitHub `main`；
2. 等待新的 Actions 运行显示绿色对勾；
3. 下载该次运行的 `plantdoctor-apk`；
4. 解压并记录 APK 对应的 Git 提交号；
5. 安装到测试手机；
6. 按验收清单重新测试。

当前是 debug APK。如果后续要正式发布、长期覆盖安装或上架应用商店，需要改用 release 构建，并妥善保管固定的 Android 签名密钥。演示阶段不要随意生成多套签名。

## 12. 常见问题

### 12.1 Actions 构建失败

点开红色运行，查看 **Build debug APK** 的最后错误。工作流还会上传 `buildozer-failure-log`，保留 7 天。不要只根据大量 warning 判断，应优先查看 `FAILED`、`error:` 和 `Command failed`附近的内容。

### 12.2 Actions 成功但页面底部没有 APK

确认打开的是具体运行页面，并已登录 GitHub。Artifact 只保留 14 天；过期后重新运行 workflow。

### 12.3 API 报“找不到模型”

确认文件不是 `pest_model.pth.pth`、`best_model.zip` 或放在项目根目录。正确路径必须是：

```text
C:\Users\21065\Desktop\PlantDoctor\ai_model\pest_model.pth
```

### 12.4 API 报权重尺寸不匹配

说明 `pest_model.pth` 不是当前 181 类 ConvNeXt-Base 权重，或 `classes.json` 与训练时不一致。使用正确模型和配套的类别文件，不要通过强行忽略错误来启动服务。

### 12.5 APK 能打开，但识别失败

先用手机浏览器访问 `http://<电脑IPv4>:8000`。浏览器不通就是网络、IP、防火墙或服务端问题；浏览器能通但 APK 不通，再检查 APK 构建时 `config.py` 中的默认地址。

### 12.6 地图空白

地图瓦片需要手机联网。它与电脑上的 `pest_model.pth` 无关，检查手机网络和地图服务是否可访问。

## 13. 演示前最终验收清单

- [ ] GitHub Actions 最新构建为绿色 `success`；
- [ ] 已下载并解压 `plantdoctor-apk`；
- [ ] APK 已安装到 ARM64 Android 手机；
- [ ] 相机和图片权限已允许；
- [ ] `ai_model/pest_model.pth` 存在且能成功加载；
- [ ] `classes.json` 与模型为同一套 181 类配置；
- [ ] FastAPI 使用 `0.0.0.0:8000` 运行；
- [ ] 手机和电脑在同一局域网；
- [ ] 手机浏览器能访问 `http://<电脑IPv4>:8000`；
- [ ] 已测试相册识别、拍照识别和 Top-5；
- [ ] 已检查别名、分布地区和防治资料；
- [ ] 已测试首页搜索、广州分布图、扫一扫和返回导航；
- [ ] 电脑已接电，并关闭演示期间的自动休眠。
