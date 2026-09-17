---
name: plantdoctor-code-style
description: Enforces Plant Doctor conventions for Kivy UI, SQLite, threading, and error handling. Use when writing, reviewing, or refactoring Python code in this repo. Do not use for ai_model scripts.
---

# Plant Doctor 代码风格指南

本项目是 **Kivy 桌面/移动端** 应用（纯 Python 构建 UI，无 .kv 文件）+ **SQLite 本地库** + **FastAPI 识别服务端**。本指南约束客户端代码（`main.py`、`config.py`、`utils.py`、`discovery.py`、`screens/`、`widgets/`、`database/`）。`ai_model/` 下的训练与服务脚本不在范围内，遵循各自脚本风格即可。

完整的风格分析（含源码证据与示例）见 [references/style-analysis.md](references/style-analysis.md)。写代码前先按下述规则执行，评审时逐条对照文末检查清单。

## 1. 文件与模块组织

- 一个页面一个文件，放在 `screens/<功能名>.py`；页面内专用的卡片/行/小组件类与页面同文件，跨页面复用的组件放 `widgets/`。
- 新页面类继承 `Screen`（需要背景图/相机通用能力时继承 `utils.BaseScreen`），并在 `main.py` 的 `ScreenManager` 中注册，`sm.current` 用的页面名与 `self.name` 字符串完全一致。
- 常量、路径、静态种子数据只写在 `config.py`（`UPPER_SNAKE_CASE`）；禁止在页面中硬编码颜色、路径、接口地址和商品/词条数据。
- 公共能力下沉：字体/弹窗/Toast/平台判断 → `utils.py`；数据库访问 → `database/`；可复用控件 → `widgets/`。页面只负责组装 UI 与交互。
- 单文件超过约 600 行或 `build_ui` 超过约 150 行时，把界面分区拆成 `_build_xxx()` 方法或独立组件类，不要继续堆积巨型方法。
- 模块导入顺序：标准库 → 第三方（Kivy 等）→ 本项目（`config` / `utils` / `database` / `widgets`），组间空行；非必需重依赖在函数内惰性导入（见第 7 节）。

## 2. 命名规范

| 对象           | 规则                                 | 示例                                             |
| -------------- | ------------------------------------ | ------------------------------------------------ |
| 文件/目录      | snake_case，页面用功能名词           | `farming_plan.py`、`user_db.py`                  |
| 页面类         | PascalCase + `Screen` 后缀           | `HomeScreen`、`PestDetailScreen`                 |
| 跨页面控件     | PascalCase，无语义前缀               | `RoundedButton`、`CircleImage`、`ProductRow`     |
| 文件内私有控件 | `_` 前缀 PascalCase                  | `_BarButton`、`_TapImage`                        |
| 函数/方法      | snake_case，动词开头                 | `build_ui`、`go_back`、`can_recognize_today`     |
| 内部实现       | `_` 前缀                             | `_connect`、`_row_to_user`、`_update_canvas`     |
| 常量           | UPPER_SNAKE_CASE，集中于 `config.py` | `GREEN`、`API_BASE_URL`、`STORE_CATALOG_VERSION` |
| 模块级单例     | UPPER_SNAKE_CASE                     | `USER_DB`、`STORE_DB`                            |
| Kivy 属性      | snake_case 声明式属性                | `product_id = NumericProperty(0)`                |
| 数据库表/列    | snake_case，表带模块前缀             | `store_products`、`community_comments`、`is_hot` |
| 布尔存储       | INTEGER 0/1，Python 侧 `bool()` 转换 | `is_featured`                                    |
| 页面名字符串   | 全小写英文，与文件名语义对应         | `self.name = "camera"`                           |
| 用户可见文案   | 用户可见文本用中文，代码标识符用英文 | 按钮 `text="知道了"`                             |

时间戳格式：日期 `"%Y-%m-%d"`，文件名 `"%Y%m%d_%H%M%S"`。

## 3. Kivy / UI 编写约定

- **全部用 Python 代码构建界面**，不新增 .kv 文件。每个页面在 `__init__` 里设置 `self.name` 后调用 `self.build_ui()`，根容器统一命名 `self.layout`（通常是 `FloatLayout`）。
- 尺寸一律使用 `dp()`、字号一律使用 `sp()`；布局优先用 `pos_hint`/`size_hint` 比例定位（设计稿基准 360×800）。
- 所有含文字的控件必须传 `**text_style()` 以应用中文字体；多行 `Label` 必须 `label.bind(size=label.setter("text_size"))`。
- 自定义圆角/圆形/圆形裁剪用 `canvas.before` 绘制（`RoundedRectangle`/`Ellipse`/Stencil），固定写法：构造函数中 `self.bind(pos=self._update_canvas, size=self._update_canvas)` 并 `Clock.schedule_once(lambda dt: self._update_canvas(), 0)`，回调内先 `canvas.before.clear()` 再重绘。
- 图片资源先 `os.path.exists()` 判断，缺失时用 `GrayPlaceholder`/字符图标兜底，禁止出现空白或崩溃。
- 控件优先复用 `widgets/base_widgets.py` 现有件（`RoundedButton`、`IconButton`、`CircleImage`、`ToolCard`、`LikeImageButton` 等），**不要在页面里重新定义等价控件**。
- 页面切换：`self.manager.current = "xxx"`；跨页面状态（当前用户、拍照模式、识别结果）通过 `App.get_running_app()` 上的属性与方法传递，不要新建全局变量。
- 生命周期：进入/离开页面用 `on_pre_enter`/`on_leave`；轮询必须在离开时 `Clock.unschedule`，相机必须在离开时释放。
- KivyMD 是**可选依赖**：使用前经 `utils.ensure_md_theme()` / `md_available()` 检查，不可用时必须有纯 Kivy 降级路径。

## 4. 数据访问层（SQLite）

- 使用标准库 `sqlite3`，每个数据库类实现 `_connect()`（设置 `row_factory = sqlite3.Row`）与 `_initialize()`（建表 + 迁移），并在模块末尾创建单例（`USER_DB = UserDatabase()`）。
- **每次操作开短连接**：`with self._connect() as conn:`，写操作后显式 `conn.commit()`；不缓存长连接。
- 值参数一律用占位符：`?` 单参数或 `:name` 配合 `executemany`。**禁止**把变量直接拼进 SQL 值；只有代码自有的表名/列名常量允许 f-string（如 `_ensure_column`），`IN` 列表用动态生成的占位符。
- 查询结果经静态映射方法转成 dict（`_row_to_user`、`_row_to_product`），数值字段显式 `int()`/`float()`/`bool()`，可空文本用 `row["x"] or ""`。
- Schema 演进：新增列用 `_ensure_column` 幂等加列；种子数据整体变更时提升 `config.STORE_CATALOG_VERSION` 并在 `app_meta` 中比对重灌。新表必须 `CREATE TABLE IF NOT EXISTS`。
- 数据库文件路径来自 `config.STORE_DB_PATH`，不允许在业务代码里写死 `smart_agri.db`。

## 5. 网络与并发

- 所有网络请求、文件对话框等阻塞操作放到 `threading.Thread(..., daemon=True)`，**禁止在 Kivy 主线程做网络调用**。
- 线程内**不得直接操作控件**；结果回投主线程统一用 `Clock.schedule_once(lambda dt: ..., 0)`。
- 异步任务统一回调签名 `on_success` / `on_error`（参考 `App.start_recognition_for_image(image_path, on_success, on_error)`、`fetch_weather(city, on_success, on_error)`）。
- HTTP 调用必须：
  - `requests.Session()` 后立即 `session.trust_env = False`（绕过系统代理，保证局域网可达）；urllib 则用 `ProxyHandler({})`；
  - 设置超时（连接/读取元组，如 `timeout=(3, 30)`）；
  - 外部返回数据先过归一化函数（如 `CameraScreen._normalize_api_result`）再进入 UI。
- 服务地址/外部接口要有多级回退（缓存地址 → 环境变量 → 默认值；主天气源 → wttr.in），回退失败给用户可理解的中文提示。
- UDP 服务发现等一次性后台任务也要 daemon 线程，超时静默回退，不阻塞进入主界面。

## 6. 错误处理与日志

- 分类处理，不允许一种 `except` 走天下：
  1. **资源清理**（相机关闭、文件句柄）：`except Exception: pass`，仅用于小步清理且前后保留原异常路径；
  2. **诊断日志**：`print("[模块] 动作失败:", exc)`，必须带方括号标签（`[camera]`、`[server]`、`[layout]`、`[album]` 等）；
  3. **面向用户**：`show_toast("中文、说清原因和下一步")` 或页面内状态标签；
  4. **可降级**：缺依赖/缺资源时走兜底实现，不崩溃（PIL→shutil、KivyMD→None、图片→占位符）。
- 布局回调中的异常必须被吞掉并打印（参考 `bind_deferred_layout`），绝不能冒泡卡死 Kivy 主循环。
- 防御式取值：外部输入用 `(x or "")`、dict 用 `.get(k) or 默认值`；文件操作前 `os.path.exists`。
- 启动期致命错误写 `crash.log`（参考 `MyApp.build()`），不要让窗口静默退出。
- 不引入 `logging` 框架，与现有代码保持一致：诊断信息一律标签化 `print`。

## 7. 注释与文档字符串

- 注释语言为中文，解释**为什么**（兼容哪个版本、绕过什么坑），而不是复述代码做什么。
- 非平凡函数写中文 docstring；兼容性黑魔法必须写明「现象 / 根因 / 处理」（参考 `utils.patch_opencv_camera`）。
- 大段代码分区用横幅：`# ───── 分区标题（可选：参考 UI/7.jpg）─────`。
- 颜色等魔法值行尾注释含义：`self.bright_green = (0.42, 0.76, 0.32, 1)  # 登录按钮、选中tab下划线`。
- 修 bug 留下的绕行代码必须附问题链接式说明或现象描述，禁止留下无注释的"奇怪写法"。

## 8. 平台兼容与可选依赖

- 平台差异一律走 `utils.is_android()` 分支；Android 权限经 `is_android_permission_granted` / `request_android_permissions`，非 Android 直接视为已授权。
- PIL、cv2、KivyMD 等可选依赖：模块顶层 `try: import ... except Exception: X = None`，使用处判空降级；或在函数内惰性导入。
- 涉及第三方库兼容补丁时：幂等（类上打 `_xxx_patched` 标记）、只在必要时 monkeypatch、失败可安全返回 False。
- 路径不要假设操作系统：用 `os.path.join` / `os.makedirs(..., exist_ok=True)`；中文字体按 `register_chinese_font` 的候选列表扩展。

## 9. 代码复用策略

- 复用顺序：先查 `widgets/` → 再查 `utils.py` → 再查同文件内已有私有组件；三者都没有才新建。
- 一个组件被第二个页面需要时，立刻从页面文件迁移到 `widgets/` 并改为无下划线公开命名，删除本地副本。
- 数据归一化/映射逻辑放数据库类静态方法或调用点附近的 `@staticmethod`，不在多个页面重复写字段兼容代码。
- 种子数据与常量只在 `config.py` 维护一份；需要变体时引用原常量，不复制粘贴。

## 10. 完成定义（提交前自检）

- [ ] 新页面已在 `main.py` 注册，页面名字符串与跳转一致；
- [ ] 无硬编码颜色/路径/URL，均来自 `config.py`；
- [ ] 所有文字控件传 `text_style()`，多行 Label 绑定 `text_size`；
- [ ] 图片/字体/可选依赖均有存在性判断与兜底；
- [ ] 网络/IO 在 daemon 线程，UI 更新经 `Clock.schedule_once`，HTTP 禁代理且有超时；
- [ ] SQL 值全部参数化，数据库改动可在删除 `smart_agri.db` 后自动重建；
- [ ] `except Exception` 属于第 6 节四类之一且有中文提示或标签日志；
- [ ] 新控件确认 `widgets/` 无重复实现；
- [ ] Windows 开发模式冒烟通过：登录 → 首页 → 拍照/选图识别 → 结果 → 社区/商城/我的；
- [ ] 未提交 `build/`、`dist/`、`*.db`、`api_url.txt`、`photos/*`、`*.pth`（见根目录 `.gitignore`）。
