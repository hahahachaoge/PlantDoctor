# 农智云警 Plant Doctor

农智云警（Plant Doctor）是一款面向农户的**智慧农业病虫害识别 APP**：拍一张作物照片，就能得到病虫害名称、置信度、症状简介与防治建议，同时集成了农资商城、种植社区、虫害百科、农事提醒与天气等常用功能。

客户端使用 **Kivy 2.3.0** 开发，一套代码同时支持 Windows 桌面运行与 Android 打包；识别能力由本地局域网内的 **FastAPI + ConvNeXt** 服务提供，图片不出局域网，隐私与速度兼顾。

- 中文文档：`README.md`（本文件）
- English：`README.en.md`

---

## 一、功能特性

| 模块 | 位置 | 说明 |
| --- | --- | --- |
| 登录 / 注册 | `screens/auth.py` | 用户名密码登录；注册可选头像与角色（免费 / VIP） |
| 首页 | `screens/home.py` | 天气卡片（wttr.in）、今日提醒、常用工具入口、病虫害搜索、底部导航 |
| 拍照识别 | `screens/camera.py` | 调用摄像头（Android 权限处理 + 竖屏预览）或从相册 / 本地选择图片，上传后端识别 |
| 识别结果 | `screens/camera.py` | 展示病虫害中文名、置信度、简介与防治方法 |
| 社区 | `screens/community.py` | 帖子列表、帖子详情、点赞、浏览计数、评论、种植经验与防治技巧文章 |
| 农资商城 | `screens/store.py` | 首页广告位与分区推荐、分类列表、商品搜索、收藏、下单、评论、农药详情 |
| 虫害百科 | `screens/encyclopedia.py` | 病虫害词条列表与详情（介绍 + 防治方法） |
| 个人中心 | `screens/mypage.py` | 头像 / 昵称 / 签名、我的收藏、我的订单 |
| 病虫害分布图 | `screens/misc.py` | 图片型展示页 |

免费用户**每天可识别 3 次**，VIP 用户不限制次数（由 `database/user_db.py` 按日期计数控制）。

---

## 二、系统架构

```text
┌──────────────────────── 客户端（Windows / Android，Kivy） ────────────────────────┐
│  main.py  ·  MyApp / ScreenManager（全局状态与页面跳转）                            │
│  screens/*  ·  登录 → 首页 → 相机 → 结果 / 社区 / 商城 / 百科 / 个人中心            │
│  database/* ·  SQLite 本地库 smart_agri.db（用户、商品、订单、社区、词条）          │
│  discovery.py · UDP:8765 监听服务端广播，命中后把地址缓存到 api_url.txt            │
└──────────────────────────────────┬────────────────────────────────────────────────┘
                                   │  HTTP multipart  POST /predict
┌──────────────────────────────────▼────────────────────────────────────────────────┐
│  ai_model/api.py  ·  FastAPI 服务，默认监听 0.0.0.0:8000                           │
│  ConvNeXt-Base（181 类分类头）· CPU 推理 · 4 向翻转 TTA · 输出 Top-5 与防治建议     │
└───────────────────────────────────────────────────────────────────────────────────┘
```

设计要点：

- **前后端分离**：APP 只负责采集图片与展示结果，模型推理集中在服务端，便于更换模型而不必重新发版。
- **地址自动发现**：客户端启动后先在局域网内监听广播，找不到时静默回退到 `api_url.txt` 中的缓存地址或 `config.py` 默认地址。
- **本地持久化**：用户、商品、订单、点赞、浏览、评论等全部存于 SQLite 单文件库，无需额外部署数据库。

---

## 三、目录结构

```text
nongzhiyunjing/
├── main.py                  # 程序入口：创建并注册所有 Screen，管理全局状态
├── config.py                # 全部常量与静态数据（API 地址、商品种子、词条、社区帖子…）
├── utils.py                 # 工具函数与基类（中文字体、Toast、弹窗、头像裁剪、BaseScreen）
├── discovery.py             # 局域网 UDP 广播发现服务端
│
├── ai_model/                # 识别服务端与模型训练脚本
│   ├── api.py               # FastAPI 接口，加载模型并提供 /predict
│   ├── pest_model.pth       # 训练好的模型权重（供 api.py 加载）
│   ├── classes.json         # 181 个类别的英文名列表
│   ├── class_list.txt       # 类别清单与各分类样本数量统计
│   ├── disease_info.json    # 病虫害中文名、简介、防治方法详情库
│   ├── train.py             # 训练脚本（ConvNeXt + 迁移学习 + 保守训练，支持断点续训）
│   ├── preprocess_data.py   # 数据预处理：统一尺寸、清洗、按 8:2 划分 train/val
│   └── download_data.py     # 下载 PlantVillage 数据集
│
├── database/                # 数据访问层
│   ├── user_db.py           # 用户注册/登录/资料更新/每日识别次数
│   └── store_db.py          # 商城、收藏、订单、社区、词条、版本控制
│
├── screens/                 # 页面层
│   ├── auth.py  home.py  camera.py  community.py
│   ├── store.py  encyclopedia.py  mypage.py  misc.py
│
├── widgets/                 # 通用 UI 组件
│   ├── base_widgets.py      # RoundedButton / CircleImage / IconButton / ToolCard …
│   └── product_widgets.py   # 商品列表行与商品滚动列表
│
├── image/  avatars/  photos/  UI/     # 图片资源与运行时生成的头像、拍照文件
├── smart_agri.db            # SQLite 数据库（首次运行自动建表并写入种子数据）
├── main.spec                # PyInstaller 打包配置（Windows exe）
├── buildozer.spec           # buildozer 打包配置（Android APK）
├── requirements.txt         # 客户端依赖
└── weather_city.json        # 天气城市缓存
```

---

## 四、环境要求

| 项目 | 要求 |
| --- | --- |
| Python | 3.11（开发与打包均在 3.11 下完成） |
| 客户端依赖 | `kivy[base]==2.3.0`、`Pillow==10.3.0`（见 `requirements.txt`） |
| 服务端依赖 | `torch`、`torchvision`、`fastapi`、`uvicorn`、`pillow`、`python-multipart` |
| Android 打包 | Linux 环境（推荐 WSL2 / Ubuntu）+ `buildozer`、`cython`、JDK 17、Android SDK/NDK 25b |
| 运行环境 | 手机与电脑需处于**同一局域网**（同一 WiFi） |

> 模型推理使用 CPU，无需显卡；若服务端有 CUDA 环境，模型仍按 `torch.device("cpu")` 加载，可自行修改。

---

## 五、快速开始

### 1. 启动识别服务端

```bash
cd ai_model
python -m pip install torch torchvision fastapi "uvicorn[standard]" pillow python-multipart
python api.py
```

启动日志会打印模型加载情况，例如：

```text
加载病虫害识别模型...
模型加载成功，可识别 181 类病虫害，其中昆虫 100 类、作物病害 81 类
已加载 xx 条病虫害详情
启动病虫害识别 API
```

浏览器访问 `http://127.0.0.1:8000`，返回 `{"message":"病虫害识别 API 已启动"}` 即表示成功。

服务端监听 `0.0.0.0:8000`，手机端请使用电脑的局域网 IP，例如 `http://192.168.0.101:8000`。

### 2. 运行客户端

```bash
python -m pip install -r requirements.txt
python main.py
```

- Windows 下窗口会自动设为 `360×800` 竖屏模拟手机比例。
- 启动后会提示"正在搜索服务器..."，随后进入登录页。

### 3. 测试账号

见 `附录.txt`：

| 账号 | 密码 | 角色 |
| --- | --- | --- |
| `zmh` | `123` | 普通用户（每天 3 次识别） |
| `zmh2` | `123` | VIP（不限次数） |

### 4. 打包 Windows 可执行文件

```bash
python -m PyInstaller main.spec
# 产物：dist/农智云警/农智云警.exe
```

`main.spec` 已把 `image/`、`avatars/`、`database/`、`screens/`、`widgets/`、`config.py`、`utils.py`、`smart_agri.db` 一并打入。

### 5. 打包 Android APK

```bash
buildozer -v android debug
# 产物：bin/plantdoctor-1.0.0-debug.apk
```

`buildozer.spec` 关键配置：`python3 + kivy==2.3.0`、竖屏、`INTERNET/CAMERA/READ_EXTERNAL_STORAGE/READ_MEDIA_IMAGES` 权限、`arm64-v8a + armeabi-v7a`、最低 API 24、NDK 25b。`ai_model/` 已被排除在打包范围之外（模型不随 APP 分发）。

---

## 六、服务端地址配置

客户端按以下优先级决定请求地址（`config.get_api_base_url()`）：

1. `api_url.txt` —— 自动发现或历史写入的缓存地址；
2. 环境变量 `PLANT_API_URL`；
3. `config.py` 中的默认值 `API_BASE_URL`。

自动发现流程（`discovery.py`）：客户端在 UDP `8765` 端口监听，服务端需周期性广播如下 JSON，命中后立即写回 `api_url.txt`：

```json
{"service": "nongzhi_api", "ip": "192.168.0.101", "port": 8000}
```

> 注意：当前 `ai_model/api.py` **未内置广播逻辑**，因此自动发现通常会超时并回退到 `api_url.txt` / 默认地址。如需启用自动发现，可在 `api.py` 启动时增加一个后台线程向 `8765` 端口周期性广播上述 JSON。

天气城市保存在 `weather_city.json`（默认 `shanghai`），可在首页切换并自动写回。

---

## 七、识别接口说明

### `GET /`

健康检查，返回 `{"message": "病虫害识别 API 已启动"}`。

### `POST /predict`

- 请求：`multipart/form-data`，字段名 `file`，值为图片文件。
- 响应示例：

```json
{
  "success": true,
  "pest_name": "番茄疫病",
  "confidence": 96.42,
  "intro": "番茄疫病包含早疫病与晚疫病……",
  "treatment": {"medicine": "-", "dosage": "-", "method": "农业防治：……"},
  "treatment_text": "农业防治：……",
  "raw_class": "Tomato_Blight",
  "top5": [
    {"chinese_name": "番茄疫病", "raw_class": "Tomato_Blight", "confidence": 96.42}
  ],
  "low_confidence": false,
  "warning": ""
}
```

| 字段 | 说明 |
| --- | --- |
| `pest_name` | 命中的病虫害中文名 |
| `confidence` | 置信度百分比（0–100） |
| `intro` | 症状简介 |
| `treatment` / `treatment_text` | 防治建议（`method` 为完整防治文本） |
| `raw_class` | 模型原始类别英文名 |
| `top5` | TTA 平均后的 Top-5 备选结果 |
| `low_confidence` / `warning` | 置信度低于 50% 时为 `true`，提示结果仅供参考 |

失败时返回 `{"success": false, "error": "..."}`。

---

## 八、识别模型

### 模型与类别

- 骨干网络：`torchvision.models.convnext_base`，仅替换分类头为 181 维。
- 类别总数 **181**：昆虫 **100** 类 + 作物病害 **81** 类（详见 `ai_model/class_list.txt`）。
- 数据集规模：**220 899** 张图片，训练集 176 653 张（80%）、验证集 44 246 张（20%）。

### 训练策略（`ai_model/train.py`）

- ConvNeXt + ImageNet-1K 迁移学习；
- **保守训练**：在交叉熵基础上加入参数偏移 L2 正则（`lambda_cons=0.01`，跳过分类器层），抑制灾难性遗忘；
- 数据增强：`Resize(256,256)` → `RandomCrop(224)` → 水平/垂直翻转 → `RandomRotation(30)` → `ColorJitter` → `RandomErasing`；
- 损失与优化：`CrossEntropyLoss(label_smoothing=0.1)` + `AdamW(lr=2e-4, weight_decay=0.01)` + `CosineAnnealingLR`；
- `batch_size=32`、最多 100 轮、早停耐心值 15，目标准确率 92.6%；
- 支持**断点续训**：每轮保存 `checkpoint_epoch_N.pth`，并输出 `best_model.pth`、`training_history.json`、`training_report.txt`；最终导出 APP 所需的 `pest_model.pth` 与 `classes.json`。

### 推理流程（`ai_model/api.py`）

1. 预处理：`Resize((256,256))` → `CenterCrop(224)` → ImageNet 均值方差归一化；
2. **TTA**：原图、水平翻转、垂直翻转、双向翻转共 4 个变体分别推理，按类别合并概率并取平均；
3. 取平均后的 Top-5，主结果取第 1 位；
4. 中文名映射：优先查 `disease_info.json`（含简介与防治方法），其次查 `api.py` 内置的 181 条 `ALIASES` 映射表，仍未覆盖时自动生成可读中文名并给出兜底文案。

### 数据准备与复现训练

```bash
cd ai_model
python download_data.py      # 下载 PlantVillage 彩色数据集（可选，约 1GB）
python preprocess_data.py    # 统一尺寸、清洗、按 8:2 划分到 train/val
python train.py              # 训练并导出 pest_model.pth / classes.json
```

> `preprocess_data.py` / `train.py` 中的输入输出路径为原作者环境（Kaggle / 本地绝对路径），复现前请先按自己的目录调整。

---

## 九、数据库说明

`smart_agri.db` 首次运行自动建表，主要表结构：

| 表 | 用途 |
| --- | --- |
| `users` | 账号、角色（free/vip）、头像、昵称、签名、每日识别次数与日期 |
| `store_products` | 商品（分类、规格、价格、库存、是否热销/精选） |
| `store_favorites` | 商品收藏（`username + product_id` 联合主键） |
| `store_comments` | 商品评论 |
| `store_orders` | 订单 |
| `community_likes` | 帖子点赞去重 |
| `community_post_stats` | 帖子浏览量 |
| `community_comments` | 帖子评论 |
| `pest_entries` | 病虫害百科词条 |
| `user_pest_reports` | 用户病虫害上报记录 |
| `app_meta` | 应用元信息，用于种子数据版本控制 |

`config.STORE_CATALOG_VERSION` 变更时，`store_db.py` 会按版本号自动重刷商品等种子数据。

---

## 十、代码结构说明

- **`config.py`**：只存放常量与静态数据，不含业务逻辑；包含 API 地址、主题色、数据库与图片路径、商品种子数据、病虫害词条、社区帖子、首页提醒文案等。
- **`utils.py`**：跨模块共用的工具与基类 —— `register_chinese_font()` 注册中文字体（Windows / Android / macOS 多路径自动探测）、`text_style()` 返回字体配置、`show_toast()` 短暂提示、`open_text_popup()` 文字弹窗、`normalize_comment_text()` 清洗评论、`save_avatar_image()` 方形裁剪头像、`is_android()` / `is_android_permission_granted()` 平台与权限判断、`BaseScreen` 带背景图的基类。
- **`database/user_db.py`**：用户注册、登录校验、资料与头像更新、`can_recognize_today()` / `increase_recognize_count()` 每日次数控制。
- **`database/store_db.py`**：商品查询与搜索、收藏、下单、评论；社区点赞 / 浏览 / 评论；病虫害与农药、肥料词条查询；基于 `app_meta` 的版本控制。
- **`widgets/`**：`RoundedButton`、`CircleImage`、`IconButton`、`UnderlineLabel`、`GrayPlaceholder`、`LikeImageButton`、`IconStat`、`ToolCard`、`PestListRow` 等通用组件，以及商品列表行与滚动列表。
- **`screens/`**：每个页面一个类，统一通过 `main.py` 的 `ScreenManager` 注册与切换；页面间跳转与识别流程由 `MyApp` 统一调度。
- **`main.py`**：入口仅做两件事 —— `build()` 创建全部页并注册；`MyApp` 维护当前用户、相机模式、拍照菜单、图片识别与结果页跳转等全局能力。

---

## 十一、使用说明

1. **登录 / 注册**：启动后进入登录页。未注册可先注册，注册时支持选择头像与角色（免费 / VIP）。
2. **首页**：查看天气与农事提醒，点击"常用工具"进入专家服务 / 农事计划 / 虫害百科 / 病虫害分布图，也可直接搜索病虫害，或从底部导航切换社区、商城、我的。
3. **拍照识别**：首页点击识别入口 → 选择"使用相机"或"使用照片" →
   - 相机：Android 需授予相机权限，预览就绪后点击圆形快门；
   - 照片：Android 使用内置文件选择器，Windows 弹出系统文件对话框；
   图片上传至服务端识别，成功后跳转结果页。免费用户每天限 3 次。
4. **查看结果**：结果页显示病虫害名称、置信度、症状简介与防治方法；可点击"再拍一个"继续识别或返回上一页。
5. **社区 / 商城 / 百科 / 我的**：可浏览帖子并点赞评论、搜索与收藏商品并下单、查阅病虫害词条、维护个人资料与查看收藏 / 订单。

---

## 十二、已知问题与注意事项

1. **商品详情页未注册**：`screens/store.py` 中的 `ProductDetailScreen` 目前是占位实现（`set_product()` 直接跳回商城），且未在 `main.py` 中注册到 `ScreenManager`；`MyApp.open_product_detail_screen()` 通过 `get_screen("product_detail")` 获取会失败并提示"打开商品失败"。需要完整商品详情时，请在 `main.py` 中注册该页并补全实现。
2. **自动发现默认不可用**：`discovery.py` 依赖服务端 UDP 广播，而 `ai_model/api.py` 未实现广播，客户端会超时后使用缓存地址。
3. **必须同一局域网**：手机与电脑不在同一 WiFi、或电脑防火墙拦截 8000 端口时，识别请求会失败。
4. **`api_url.txt` 会随运行写入**：内容为本机局域网 IP，提交代码时建议忽略，避免覆盖他人配置。
5. **Kivy 相机补丁**：Windows 下 `kivy/core/camera/camera_opencv.py` 曾被手动修改（见 `附录.txt`），更换 Kivy 版本后需重新确认；`screens/camera.py` 中也已内置对 Kivy 2.3.0 `CameraOpenCV` 缺少 `fps` 属性的兼容处理。
6. **模型与数据集较大**：`pest_model.pth` 与数据集不随 APK 分发，Android 端必须联网使用服务端识别。
7. **仓库内存在项目名不一致的遗留**：正式名称为**农智云警**（见 `main.spec` 的 `name`、`screens/auth.py` 的欢迎文案、`ai_model/preprocess_data.py` 中的 `D:\农智云警\` 路径）。但 `dist/` 下已有构建产物目录名为 `农智慧眼`，`config.py` 中 `COMMUNITY_ARTICLES` 的官方账号 `username` 仍写作 `智农慧眼`。重新打包前建议统一命名，避免混淆。

---

## 十三、参与贡献

1. Fork 本仓库；
2. 新建 `Feat_xxx` 分支；
3. 提交代码；
4. 新建 Pull Request。

---

## 十四、致谢与参考

- [Kivy](https://kivy.org/) —— 跨平台 Python GUI 框架；
- [PyTorch / torchvision](https://pytorch.org/) —— ConvNeXt 模型与训练；
- [FastAPI](https://fastapi.tiangolo.com/) —— 识别服务；
- [PlantVillage Dataset](https://github.com/spMohanty/PlantVillage-Dataset) —— 作物病害图像数据；
- [wttr.in](https://wttr.in/) —— 免费天气接口。

---

## 十五、许可证

本仓库当前未包含 `LICENSE` 文件。如需转载、二次开发或商用，请先联系作者确认授权。
