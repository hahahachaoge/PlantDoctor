# Plant Doctor (农智云警)

Plant Doctor (农智云警) is a **smart-agriculture pest & disease recognition app** for growers. Take a photo of a crop and get the pest/disease name, confidence, symptom description and treatment advice — together with an integrated agro-store, farming community, pest encyclopedia, farming reminders and weather.

The client is built with **Kivy 2.3.0**, so the same codebase runs on Windows and can be packaged for Android. Recognition is powered by a **FastAPI + ConvNeXt** service running on the local network, so photos never leave your LAN.

- Chinese documentation: `README.md`
- English: `README.en.md` (this file)

---

## 1. Features

| Module | Source | Description |
| --- | --- | --- |
| Login / Register | `screens/auth.py` | Username & password login; registration with avatar and role (Free / VIP) |
| Home | `screens/home.py` | Weather card (wttr.in), daily reminders, tool shortcuts, pest search, bottom navigation |
| Camera recognition | `screens/camera.py` | Camera capture (Android permissions + portrait preview) or pick from album/file, then upload for recognition |
| Result | `screens/camera.py` | Chinese pest name, confidence, description and treatment advice |
| Community | `screens/community.py` | Post list & detail, likes, view counts, comments, farming articles |
| Store | `screens/store.py` | Banners and sectioned recommendations, category lists, search, favorites, orders, comments, pesticide detail |
| Encyclopedia | `screens/encyclopedia.py` | Pest/disease entries with intro and treatment |
| Profile | `screens/mypage.py` | Avatar / nickname / signature, my favorites, my orders |
| Pest distribution map | `screens/misc.py` | Image-only display page |

Free users are limited to **3 recognitions per day**; VIP users are unlimited (enforced by `database/user_db.py` with a per-day counter).

---

## 2. Architecture

```text
┌──────────────────────── Client (Windows / Android, Kivy) ──────────────────────────┐
│  main.py       ·  MyApp / ScreenManager (global state & navigation)                │
│  screens/*     ·  login → home → camera → result / community / store / profile     │
│  database/*    ·  local SQLite smart_agri.db (users, products, orders, community)  │
│  discovery.py  ·  listens on UDP:8765 for the server broadcast, caches api_url.txt │
└──────────────────────────────────┬─────────────────────────────────────────────────┘
                                   │  HTTP multipart  POST /predict
┌──────────────────────────────────▼─────────────────────────────────────────────────┐
│  ai_model/api.py  ·  FastAPI, listening on 0.0.0.0:8000                            │
│  ConvNeXt-Base (181-class head) · CPU inference · 4-flip TTA · Top-5 + treatment   │
└────────────────────────────────────────────────────────────────────────────────────┘
```

Design notes:

- **Separation of concerns** — the app only captures photos and renders results; inference lives on the server, so the model can be upgraded without shipping a new APK.
- **Server auto-discovery** — the client listens for a LAN broadcast at startup and silently falls back to the cached address in `api_url.txt`, then to the default in `config.py`.
- **Local persistence** — users, products, orders, likes, views and comments all live in a single SQLite file; no extra database is required.

---

## 3. Project layout

```text
nongzhiyunjing/
├── main.py                  # Entry point: creates and registers all screens, global state
├── config.py                # Constants & static data (API URL, product seeds, entries, posts…)
├── utils.py                 # Helpers & base classes (CJK font, toast, popups, avatar crop, BaseScreen)
├── discovery.py             # LAN UDP broadcast discovery of the server
│
├── ai_model/                # Recognition server and training scripts
│   ├── api.py               # FastAPI app loading the model, exposes /predict
│   ├── pest_model.pth       # Trained weights used by api.py
│   ├── classes.json         # The 181 class names
│   ├── class_list.txt       # Class inventory with per-class sample counts
│   ├── disease_info.json    # Chinese names, descriptions and treatment advice
│   ├── train.py             # Training (ConvNeXt + transfer learning + conservative training)
│   ├── preprocess_data.py   # Resize, clean, and split data 8:2 into train/val
│   └── download_data.py     # Downloads the PlantVillage dataset
│
├── database/
│   ├── user_db.py           # Registration, login, profile, daily recognition quota
│   └── store_db.py          # Store, favorites, orders, community, entries, versioning
│
├── screens/                 # Page layer
│   ├── auth.py  home.py  camera.py  community.py
│   ├── store.py  encyclopedia.py  mypage.py  misc.py
│
├── widgets/                 # Shared UI components
│   ├── base_widgets.py      # RoundedButton / CircleImage / IconButton / ToolCard …
│   └── product_widgets.py   # Product row and product scroll list
│
├── image/  avatars/  photos/  UI/     # Assets, runtime avatars and captured photos
├── smart_agri.db            # SQLite DB (tables and seed data created on first run)
├── main.spec                # PyInstaller config (Windows executable)
├── buildozer.spec           # buildozer config (Android APK)
├── requirements.txt         # Client dependencies
└── weather_city.json        # Cached weather city
```

---

## 4. Requirements

| Item | Requirement |
| --- | --- |
| Python | 3.11 (development and packaging were done on 3.11) |
| Client deps | `kivy[base]==2.3.0`, `Pillow==10.3.0` (see `requirements.txt`) |
| Server deps | `torch`, `torchvision`, `fastapi`, `uvicorn`, `pillow`, `python-multipart` |
| Android build | Linux (WSL2 / Ubuntu recommended) + `buildozer`, `cython`, JDK 17, Android SDK / NDK 25b |
| Network | Phone and PC must be on the **same LAN** (same Wi-Fi) |

> Inference runs on CPU; no GPU is needed. Even with CUDA available, the model is loaded on `torch.device("cpu")` — change it in `api.py` if you want GPU inference.

---

## 5. Getting started

### 5.1 Start the recognition server

```bash
cd ai_model
python -m pip install torch torchvision fastapi "uvicorn[standard]" pillow python-multipart
python api.py
```

Example startup log:

```text
加载病虫害识别模型...
模型加载成功，可识别 181 类病虫害，其中昆虫 100 类、作物病害 81 类
已加载 xx 条病虫害详情
启动病虫害识别 API
```

Open `http://127.0.0.1:8000`; a `{"message":"病虫害识别 API 已启动"}` response means the service is up.

The server binds `0.0.0.0:8000`; on a phone use the PC's LAN IP, e.g. `http://192.168.0.101:8000`.

### 5.2 Run the client

```bash
python -m pip install -r requirements.txt
python main.py
```

- On Windows the window is resized to a `360×800` portrait phone ratio.
- The app shows "正在搜索服务器..." (searching for server) and then opens the login page.

### 5.3 Test accounts

From `附录.txt`:

| Username | Password | Role |
| --- | --- | --- |
| `zmh` | `123` | Free user (3 recognitions/day) |
| `zmh2` | `123` | VIP (unlimited) |

### 5.4 Build the Windows executable

```bash
python -m PyInstaller main.spec
# Output: dist/农智云警/农智云警.exe
```

`main.spec` bundles `image/`, `avatars/`, `database/`, `screens/`, `widgets/`, `config.py`, `utils.py` and `smart_agri.db`.

### 5.5 Build the Android APK

```bash
buildozer -v android debug
# Output: bin/plantdoctor-1.0.0-debug.apk
```

Key `buildozer.spec` settings: `python3 + kivy==2.3.0`, portrait, permissions `INTERNET/CAMERA/READ_EXTERNAL_STORAGE/READ_MEDIA_IMAGES`, ABIs `arm64-v8a + armeabi-v7a`, min API 24, NDK 25b. The `ai_model/` directory is excluded from the build — the model is not shipped inside the app.

---

## 6. Server address configuration

The client resolves the API base URL in this order (`config.get_api_base_url()`):

1. `api_url.txt` — cached address written by auto-discovery or by the app itself;
2. environment variable `PLANT_API_URL`;
3. the default `API_BASE_URL` in `config.py`.

Auto-discovery (`discovery.py`): the client listens on UDP port `8765`. The server should periodically broadcast:

```json
{"service": "nongzhi_api", "ip": "192.168.0.101", "port": 8000}
```

On a hit the client writes the address back to `api_url.txt`.

> Note: `ai_model/api.py` currently has **no broadcast implementation**, so auto-discovery times out and the client falls back to `api_url.txt` / the default address. To enable it, add a background thread in `api.py` that periodically broadcasts the JSON above to port `8765`.

The weather city is stored in `weather_city.json` (default `shanghai`) and can be switched from the home page.

---

## 7. Recognition API

### `GET /`

Health check, returns `{"message": "病虫害识别 API 已启动"}`.

### `POST /predict`

- Request: `multipart/form-data`, field name `file`.
- Response:

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

| Field | Meaning |
| --- | --- |
| `pest_name` | Matched Chinese pest/disease name |
| `confidence` | Confidence percentage (0–100) |
| `intro` | Symptom description |
| `treatment` / `treatment_text` | Treatment advice (`method` holds the full text) |
| `raw_class` | Raw model class name |
| `top5` | Top-5 alternatives after TTA averaging |
| `low_confidence` / `warning` | `true` when confidence < 50%, results for reference only |

On failure it returns `{"success": false, "error": "..."}`.

---

## 8. The model

### Model and classes

- Backbone: `torchvision.models.convnext_base`, with the classifier head replaced by a 181-way linear layer.
- **181 classes** total: **100** insect classes + **81** crop-disease classes (see `ai_model/class_list.txt`).
- Dataset: **220,899** images — 176,653 for training (80%) and 44,246 for validation (20%).

### Training (`ai_model/train.py`)

- ConvNeXt with ImageNet-1K transfer learning;
- **Conservative training**: an L2 parameter-drift penalty (`lambda_cons=0.01`, skipping the classifier) added to cross-entropy to limit catastrophic forgetting;
- Augmentation: `Resize(256,256)` → `RandomCrop(224)` → horizontal/vertical flips → `RandomRotation(30)` → `ColorJitter` → `RandomErasing`;
- Loss/optimizer: `CrossEntropyLoss(label_smoothing=0.1)` + `AdamW(lr=2e-4, weight_decay=0.01)` + `CosineAnnealingLR`;
- `batch_size=32`, up to 100 epochs, early-stop patience 15, target accuracy 92.6%;
- **Resumable**: a `checkpoint_epoch_N.pth` per epoch, plus `best_model.pth`, `training_history.json` and `training_report.txt`; the final export is `pest_model.pth` + `classes.json` for the app.

### Inference (`ai_model/api.py`)

1. Preprocessing: `Resize((256,256))` → `CenterCrop(224)` → ImageNet normalization;
2. **TTA**: four variants (original, horizontal flip, vertical flip, both) are inferred and their per-class probabilities averaged;
3. Top-5 from the averaged probabilities; the first entry is the main result;
4. Name mapping: first `disease_info.json` (description + treatment), then the built-in 181-entry `ALIASES` table, and finally an auto-generated readable name with fallback text.

### Data preparation and reproducing training

```bash
cd ai_model
python download_data.py      # optional: download PlantVillage color dataset (~1 GB)
python preprocess_data.py    # resize, clean, split 8:2 into train/val
python train.py              # train and export pest_model.pth / classes.json
```

> The paths in `preprocess_data.py` / `train.py` are the original author's environment (Kaggle / local absolute paths). Adjust them before reproducing.

---

## 9. Database

`smart_agri.db` is created automatically on first run. Main tables:

| Table | Purpose |
| --- | --- |
| `users` | Account, role (free/vip), avatar, nickname, signature, daily recognition count and date |
| `store_products` | Products (category, spec, price, stock, hot/featured flags) |
| `store_favorites` | Favorites (`username + product_id` composite key) |
| `store_comments` | Product comments |
| `store_orders` | Orders |
| `community_likes` | De-duplicated post likes |
| `community_post_stats` | Post view counts |
| `community_comments` | Post comments |
| `pest_entries` | Encyclopedia entries |
| `user_pest_reports` | User-submitted pest reports |
| `app_meta` | App metadata used for seed-data versioning |

When `config.STORE_CATALOG_VERSION` changes, `store_db.py` re-seeds product data automatically by version.

---

## 10. Code organization

- **`config.py`** — constants and static data only, no logic: API URL, theme color, database and image paths, product seeds, pest entries, community posts, home reminders.
- **`utils.py`** — shared helpers and base classes: `register_chinese_font()` (auto-detects CJK fonts on Windows / Android / macOS), `text_style()`, `show_toast()`, `open_text_popup()`, `normalize_comment_text()`, `save_avatar_image()` (square crop), `is_android()` / `is_android_permission_granted()`, and the background-image `BaseScreen`.
- **`database/user_db.py`** — registration, credential check, profile/avatar updates, and `can_recognize_today()` / `increase_recognize_count()` quota control.
- **`database/store_db.py`** — product queries & search, favorites, orders, comments; community likes / views / comments; pesticide and fertilizer entries; versioning via `app_meta`.
- **`widgets/`** — `RoundedButton`, `CircleImage`, `IconButton`, `UnderlineLabel`, `GrayPlaceholder`, `LikeImageButton`, `IconStat`, `ToolCard`, `PestListRow`, plus product list widgets.
- **`screens/`** — one class per page, all registered in `main.py`'s `ScreenManager`; navigation and the recognition flow are coordinated by `MyApp`.
- **`main.py`** — the entry point only does two things: `build()` creates and registers every screen; `MyApp` owns global state (current user, camera mode) and global actions (capture menu, image recognition, result navigation).

---

## 11. Usage

1. **Login / Register** — the app opens on the login page; new users can register with an avatar and role (Free / VIP).
2. **Home** — weather and farming reminders, tool shortcuts (expert service, farming plan, encyclopedia, distribution map), pest search, and bottom navigation to community / store / profile.
3. **Recognition** — tap the recognition entry and choose "camera" or "photo":
   - Camera: requires the Android camera permission; tap the round shutter once the preview is ready.
   - Photo: the built-in file chooser on Android, the native file dialog on Windows.
   The image is uploaded to the server and the result page opens on success. Free users are limited to 3 per day.
4. **Result** — pest name, confidence, description and treatment; "retake" starts a new recognition.
5. **Community / Store / Encyclopedia / Profile** — browse and like posts, search and favorite products and place orders, read encyclopedia entries, manage profile, favorites and orders.

---

## 12. Known issues

1. **Product detail page is not registered** — `ProductDetailScreen` in `screens/store.py` is a placeholder (`set_product()` just navigates back to the store) and is never added to the `ScreenManager` in `main.py`. `MyApp.open_product_detail_screen()` therefore fails on `get_screen("product_detail")` and shows "打开商品失败". Register and implement the page if you need a full product detail view.
2. **Auto-discovery is effectively unavailable** — `discovery.py` expects a server UDP broadcast that `ai_model/api.py` does not implement, so it times out and the cached address is used.
3. **Same LAN required** — if the phone and PC are on different networks, or port 8000 is blocked by the firewall, recognition requests fail.
4. **`api_url.txt` is written at runtime** — it contains your machine's LAN IP; consider ignoring it in version control.
5. **Kivy camera patch** — on Windows `kivy/core/camera/camera_opencv.py` was modified manually (see `附录.txt`); re-verify after upgrading Kivy. `screens/camera.py` also contains a compatibility shim for the missing `fps` attribute of `CameraOpenCV` in Kivy 2.3.0.
6. **Large assets** — `pest_model.pth` and the dataset are not shipped in the APK, so the Android app must be online to use the server.

---

## 13. Contributing

1. Fork the repository;
2. Create a `Feat_xxx` branch;
3. Commit your changes;
4. Open a Pull Request.

---

## 14. Acknowledgements

- [Kivy](https://kivy.org/) — cross-platform Python GUI framework;
- [PyTorch / torchvision](https://pytorch.org/) — ConvNeXt model and training;
- [FastAPI](https://fastapi.tiangolo.com/) — recognition service;
- [PlantVillage Dataset](https://github.com/spMohanty/PlantVillage-Dataset) — crop disease imagery;
- [wttr.in](https://wttr.in/) — free weather API.

---

## 15. License

This repository does not currently include a `LICENSE` file. Please contact the author for permission before redistributing, modifying or using it commercially.
