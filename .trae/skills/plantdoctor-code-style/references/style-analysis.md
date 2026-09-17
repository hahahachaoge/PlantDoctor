# Plant Doctor 项目风格分析报告

> 本报告基于对 `main.py`、`config.py`、`utils.py`、`discovery.py`、`screens/`（9 个页面文件，约 6600 行）、`widgets/`（2 个组件文件）、`database/`（2 个数据访问文件）的实际代码审阅整理，所有结论均可在对应文件中复核。它是 `SKILL.md` 规则的依据与示例库。

## 1. 总体画像

一个由小团队（疑似课程项目）演进而来的 Kivy 单体客户端：**纯 Python 命令式 UI、无 .kv 文件、SQLite 零部署、HTTP 解耦的识别后端、防御式降级遍布全项目**。代码风格高度统一（中文注释、统一的弹窗/Toast/字体工具、统一的数据库访问范式），但存在"页面文件偏大、局部控件重复定义"的成长型债务。

关键数字：

| 指标 | 值 |
| --- | --- |
| 页面类数量 | 19 个（screens/ 共 29 个类，含页面内嵌组件） |
| 最大页面文件 | `screens/home.py` 1227 行、`screens/mypage.py` 1184 行 |
| `except Exception` 出现次数 | 60 次（14 个文件） |
| 网络/线程/UI 调度/提示原语调用 | 219 次（19 个文件，含 Clock 调度、线程、Toast、print） |

## 2. 代码组织结构

### 2.1 分层

```text
main.py            应用入口 + 全局协调者（App 子类、ScreenManager、识别调度、文件选择）
config.py          常量层（颜色、路径、接口地址、静态种子数据），无业务逻辑
utils.py           横切工具层（字体、弹窗、Toast、平台判断、相机兼容、BaseScreen）
discovery.py       网络发现（UDP:8765 监听，回调式）
screens/           表现层：每页一个 Screen 子类 + 同文件专用小部件
widgets/           复用控件层（base_widgets.py / product_widgets.py）
database/          数据访问层（user_db.py / store_db.py，模块级单例）
smart_agri.db      SQLite 存储（运行时自动生成）
ai_model/          独立的 FastAPI 服务端与训练脚本（不在客户端风格约束内）
```

依赖方向单向向下：`screens → widgets/utils/database → config`；跨页面协调反向通过 `App.get_running_app()`，不直接互相 import 页面。

### 2.2 页面文件的内部结构（统一模板）

以 `screens/camera.py`、`screens/auth.py` 为代表，每个页面类遵循固定骨架：

1. `__init__(**kwargs)`：`super().__init__` → `self.name = "xxx"` → 状态字段初始化 → `self.build_ui()`；
2. `build_ui(self)`：创建 `self.layout = FloatLayout()`，按区块顺序 `add_widget`，区块前有中文注释（`# 头像区域`、`# 品牌名称`）；
3. `_update_xxx(self, *_args)`：canvas 重绘回调；
4. `on_pre_enter` / `on_leave`：资源申请与释放（权限、相机、轮询）；
5. 业务方法（`go_back`、`take_photo` 等）与 `@staticmethod` 归一化方法。

页面专用的卡片/行组件与页面同文件（如 `store.py` 的 `PesticideCard`、`farming_plan.py` 的 `PlanItemCard`、`mypage.py` 的 `OrderRow`），跨页面复用后才升级到 `widgets/`。

### 2.3 组织上的已知债务（新代码应避免继续扩大）

- 页面文件 600–1200 行，`build_ui` 是事实上的巨型方法（如 `home.py`、`mypage.py`）；
- 等价控件多处重复：`widgets/base_widgets.py:IconButton`、`screens/home.py:_IconButton`、`screens/community.py:_BarButton`/`_TapImage` 是同一思路的多份实现；`home.py:HomeToolCard` 与 `widgets/base_widgets.py:ToolCard` 职责重叠。

## 3. 命名规范

### 3.1 实际用法

| 类别 | 约定 | 证据 |
| --- | --- | --- |
| 文件名 | snake_case 功能名 | `user_db.py`、`base_widgets.py`、`farming_plan.py` |
| 页面类 | `XxxScreen` | `LoginScreen`、`CommunityDetailScreen`、`PesticideDetailScreen` |
| 复用控件 | PascalCase 名词 | `RoundedButton`、`CircleImage`、`LikeImageButton`、`ProductRow` |
| 文件内私有控件 | `_PascalCase` | `_BarButton`、`_TapImage`、`_IconButton`、`_HBarButton` |
| 公开方法 | snake_case 动词短语 | `build_ui`、`setup_background`、`increase_recognize_count`、`fetch_weather` |
| 内部方法 | `_snake_case` | `_connect`、`_initialize`、`_ensure_column`、`_row_to_user`、`_release_camera`、`_normalize_api_result` |
| 常量/单例 | UPPER_SNAKE | `GREEN`、`IMAGE_DIR`、`API_BASE_URL`、`STORE_CATALOG_VERSION`、`USER_DB`、`STORE_DB` |
| Kivy 属性 | snake_case 声明属性 | `product_widgets.py` 中 `product_id`、`name_text`、`screen_ref` |
| 数据库对象 | 模块前缀 + 复数表名 | `store_products`、`store_favorites`、`community_likes`、`community_post_stats`、`user_pest_reports`、`app_meta` |
| 布尔列 | `is_xxx`，INTEGER 0/1 | `is_hot`、`is_featured`，映射时 `bool(row["is_hot"])` |
| 页面名 | 小写字面量 | `self.name = "login" / "camera"`，`manager.current = "home"` |
| 文案 | 中文 | `text="知道了"`、Toast `"识别中，请稍候..."` |
| 时间格式 | 固定 strftime | 日期 `%Y-%m-%d`；拍照文件 `capture_%Y%m%d_%H%M%S.png` |

### 3.2 注意点

- 查询类方法用 `get_*`/`can_*` 表达返回语义（`get_user`、`can_recognize_today`、`username_exists`），写操作动词明确（`create_user`、`reset_daily_recognize_if_needed`、`increase_recognize_count`）。
- 私有前缀语义稳定：`_` 表示"仅本类/本模块使用"，如 `_canonicalize_row`、`_wait_for_texture`。
- 回调参数命名固定为 `on_success` / `on_error`，实例参数惯例为 `_instance`/`*_args`（Kivy bind 回调）。

## 4. 注释风格

- **语言**：全部中文；技术标识符英文，形成"英文命名 + 中文注释"的稳定搭配。
- **行内注释解释 why**：

  ```python
  session.trust_env = False           # 不走系统代理
  # 离开页面时停止轮询并彻底释放摄像头，避免设备被占用、
  # 也避免后台继续每帧刷新报错日志。
  ```

- **docstring 用于非平凡逻辑**，且兼容黑魔法采用「现象 / 根因 / 处理」三段式，见 `utils.py:patch_opencv_camera`；「目的」式见 `probe_camera_index`。
- **分区横幅**：`# ───── 摄像头兼容（OpenCV 5.x / Kivy 2.3.0）─────`、`# ───── 识别结果页（参考 UI/7.jpg）─────`，并注明对应的设计稿文件。
- **魔法值就地注释**：`self.bright_green = (0.42, 0.76, 0.32, 1)  # 登录按钮、选中tab下划线`。
- **函数 docstring 风格**：简短中文一句话 + 空行 + 背景说明（`ensure_md_theme`、`bind_deferred_layout`、`fetch_weather`）。
- 几乎没有 `TODO`/`FIXME` 残留，也没有自动生成的冗余 docstring。

## 5. 设计模式与架构惯用法

| 模式/惯用法 | 实现方式 | 证据 |
| --- | --- | --- |
| 模块级单例 | 类定义后立即实例化，全项目 import 同一对象 | `user_db.py` 末尾 `USER_DB = UserDatabase()`；`STORE_DB` 同理 |
| 中央协调者（Mediator） | `MyApp` 持有 `current_user`、`camera_mode`、`previous_before_camera`、识别调度、加载弹窗；页面不互相持有 | 各页面 `app = App.get_running_app()` 后调用 `app.start_recognition_for_image(...)` |
| ScreenManager 导航 | 字符串页面名 + `manager.current`；相机页用 `previous_before_camera` 记忆来源 | `BaseScreen.open_camera`、`CameraScreen.go_back` |
| 模板方法基类 | `BaseScreen(Screen)` 提供 `setup_background`、`open_camera`、相对坐标工具 | `utils.py`；`screens/misc.py:MapScreen(BaseScreen)` |
| 回调式异步 | 后台线程 + `on_success`/`on_error` 回调，结果经 `Clock.schedule_once` 回主线程 | `main.py:start_recognition_for_image`、`home.py:fetch_weather`、`discovery.py:start_server_discovery` |
| 行映射器（Mapper） | sqlite Row → 业务 dict，集中做类型转换与默认值 | `_row_to_user`、`_row_to_product`、`CameraScreen._normalize_api_result` |
| 工厂式兜底 | 资源存在用图片，不存在用字符/占位控件 | `auth.py:_input_icon(filename, fallback_text)`、`IconStat`/`ToolCard` 的 icon 二选一 |
| 幂等 Monkey Patch | 类上打 `_version_patched` 标记，只补一次 | `utils.patch_opencv_camera` |
- 可选依赖降级 | 顶层 try-import 置 None，调用处判空 | PIL（`save_avatar_image` 退回 `shutil.copyfile`）、KivyMD（`ensure_md_theme` 失败标志缓存）、cv2（`probe_camera_index` 返回 0） |
| 声明式属性 | 仅在需要 kv 式绑定的复用组件上使用 Kivy Property | `widgets/product_widgets.py`（7 个 Property）；全项目仅 9 处，页面主体仍用普通属性 + 命令式刷新 |
| 版本化数据迁移 | `app_meta` 存 `store_catalog_version`，版本不符重灌种子；`_ensure_column` 做列级迁移 | `database/store_db.py:_initialize` |
| 惰性导入 | 避免硬依赖/循环导入/启动崩溃 | `open_text_popup` 内部导入 `RoundedButton`；`main.py` 在方法内 `import_module("requests")` |

## 6. 技术栈使用特点

### 6.1 Kivy 用法

- **无 .kv 文件**，界面全部 Python 命令式构造；设计基准窗口 360×800 竖屏（`main.py` 中设置）。
- 度量单位纪律严格：布局数值几乎全部 `dp()`，字号全部 `sp()`；定位以 `pos_hint` 比例为主。
- 自绘范式统一：`canvas.before.clear()` → `with ... : Color(...) + RoundedRectangle/Ellipse`，并 bind `pos/size` 重绘（`RoundedButton`、`GrayPlaceholder`、`CircleImage`、拍照按钮圆环）。
- 中文字体：`LabelBase.register(name="ChineseFont", ...)` 多平台候选路径；所有文字控件以 `**text_style()` 注入 `font_name`，未注册成功时返回 `{}` 自然降级。
- 生命周期纪律：相机页 `on_pre_enter` 申请权限/竖屏，`on_leave` 取消轮询并逐步释放（`play=False` → `_device.release()` → 移除控件，每步独立 try）。
- 线程边界纪律：网络线程只做请求与解析，UI 回调一律 `Clock.schedule_once` 包裹（`main.py` 中成功/HTTP 异常/连接异常三条路径均如此）。

### 6.2 数据访问

- 标准库 `sqlite3`，`row_factory = sqlite3.Row`；**每方法短连接**（`with self._connect() as conn:`），无连接池、无 ORM。
- 参数化到位：值用 `?` 或 `:name`；动态 `IN` 列表先生成占位符再传参（`store_db.py` 的 `f"... IN ({placeholders})"`，`placeholders` 由代码生成，不接外部输入）。
- 建表幂等（`CREATE TABLE IF NOT EXISTS`），迁移两级：列级 `_ensure_column`，目录级版本号重灌。
- 种子数据外置在 `config.py`，`executemany` 批量写入。

### 6.3 网络

- 识别接口：`requests.Session()` + `trust_env=False` + 显式超时；服务地址四级解析（`api_url.txt` 缓存 → 环境变量 → 默认地址 → 连通性探测回退，成功后写回缓存）。
- 天气：主源 itboy（`urllib` + `ProxyHandler({})` 禁代理 + 8 秒超时），失败回退 wttr.in，城市代码本地映射。
- 服务发现：UDP 8765 监听 5 秒，命中回调写地址，超时静默回退。

### 6.4 打包与平台

- Windows：PyInstaller（`main.spec` 打入资源与数据库）；Android：Buildozer（权限、ABI、NDK 版本在 `buildozer.spec` 声明）。
- 平台分支集中在 `utils.is_android()`；Android 权限/文件选择走 `android.permissions`/`android.permissions.request_android_permissions` 风格的 importlib 惰性调用。

## 7. 错误处理方式

`except Exception` 共 60 处，但呈四种明确策略，而非吞异常：

1. **静默清理型**：资源释放多步操作，每步独立 try，失败 `pass`（`CameraScreen._release_camera` 连续三段）；
2. **标签日志型**：`print("[camera] init_camera 兼容重建失败:", exc)`、`[layout]`、`[server]`、`[album]`、`[kivymd]`，前缀即模块定位；
3. **用户提示型**：错误最终落到 `show_toast`/状态标签，文案中文、含原因与建议，如 `免费用户每天限识别3次，升级VIP解锁无限次`、`识别服务返回异常: {status_code}（{url}）`；
4. **降级回退型**：依赖缺失 → 替代实现；主接口失败 → 备用接口；图片缺失 → 占位控件；地址不通 → 探测候选地址。

其他特征：

- 主循环保护：`bind_deferred_layout` 在下一帧执行布局回调，内部 catch 并打印，专门用来打断"尺寸变化→回调→改尺寸"的递归回环（docstring 记录了真实事故现象）。
- 启动兜底：`MyApp.build()` 整体 try，失败把 traceback 写 `crash.log`，避免静默闪退。
- 防御式输入：`(raw_text or "").replace(...)`、`normalized.get("pest_name") or "未知病虫害"`、`row["x"] or ""`。
- 并发状态位：`capture_in_progress` 防重入；相机纹理就绪前用轮询计数 `_texture_check_count` 等待。
- 没有引入 `logging`，全项目统一用带标签的 `print`——新代码应保持一致，不要单文件引入 logging 造成风格分裂。

## 8. 代码复用策略

- **三级复用渠道**：`widgets/`（跨页面控件）→ `utils.py`（横切函数/基类）→ `config.py`（常量与种子数据）。
- **同文件私有件**：只在单页使用的卡片与行（`DateCell`、`PlanItemCard`、`PesticideCard`、`OrderRow`、`CoverImage`）与页面同文件，以 `_` 或直白命名区分。
- **组合优先**：可点击能力统一通过多继承混入 `ButtonBehavior` + 展示控件获得（`IconButton(ButtonBehavior, Label)`、`ClickableBox(ButtonBehavior, BoxLayout)`、`RoundedImage(ButtonBehavior, KImage)`），而不是给每个控件写事件系统。
- **归一化前置**：外部数据（识别 API 返回）在进入展示层前由静态方法统一成内部契约（置信度 0–1、treatment 统一为 dict、缺省文案），UI 不再兼容多种返回形状。
- **待改进的复用点**（评审时应推动收敛）：`IconButton` 与各页面 `_IconButton`/`_BarButton` 合并；`HomeToolCard` 与 `ToolCard` 合并；图标存在性判断（`os.path.exists(icon)` + 字符回退）应继续统一走 `IconStat`/`ToolCard` 既有分支，不再手写第三遍。

## 9. 给评审者的典型红旗

出现以下情况应要求修改：

1. 在页面里硬编码 URL、颜色、文件路径，或复制了一份种子数据；
2. 网络请求出现在主线程，或线程内直接改控件；
3. 新建 HTTP 调用却没有 `trust_env=False`/`ProxyHandler({})` 或没有超时；
4. SQL 用字符串拼接值参数；
5. 文字控件未传 `text_style()` 导致 Android 中文方框；
6. 图片/可选依赖未做存在性/导入保护；
7. 新写了与 `widgets/` 等价的控件；
8. `except Exception: pass` 既无注释也无日志，且不属于资源清理；
9. 页面新增功能后未在 `main.py` 注册，或跳转名与 `self.name` 不一致；
10. 提交中包含 `build/`、`dist/`、`smart_agri.db`、`api_url.txt`、`photos/*`、`*.pth`。
