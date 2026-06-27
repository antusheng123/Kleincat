# Klein Cat Desktop Pet — Codex 开发规格说明 v0.2

> 本文档用于作为 Codex 开发项目时的唯一规格依据。它整合了原始《KleinCatPet_Project_Summary》、当前已经完成的 PNG 序列帧资产处理结果，以及后续分阶段开发要求。若旧文档中仍出现 GIF、QMovie 或 `assets/*.gif` 的表述，以本文档为准。

---

## 0. 文档结论先行

本项目要构建一个基于 **PyQt6** 的 Windows 桌面宠物程序。角色是“克莱恩小黑猫”，在桌面上以透明窗口形式常驻，支持待机动画、交互动画、滚轮反馈动画、拖拽移动、右键菜单、网速监控、Todo 面板、全屏自动隐藏、滚轮调节亮度，以及通过大模型生成短句对白。

当前最重要的开发约束是：

1. **动画资产不是 GIF，而是已经抠好黑色背景的透明 PNG 序列帧。**
2. **动画播放必须在 `modules/window.py` 中使用 `QTimer + QPixmap` 实现，不允许使用 `QMovie`。**
3. **三组动画在切换时必须保持相同视窗大小，基础尺寸锁定为 `200 x 200`。**
4. **大模型 API 请求必须通过 `QThread` 异步执行，绝不能阻塞 PyQt6 主线程。**
5. **Codex 开发时必须分阶段输出，不要一次性生成全部文件。**

---

## 1. 项目名称

**Klein Cat Desktop Pet**

中文名称：**克莱恩小黑猫桌宠**。

---

## 2. 项目目标

本项目是一个面向 Windows 桌面环境的轻量化桌宠客户端，目标是让一只 Q 版小黑猫长期常驻桌面，同时尽量减少对系统资源和用户操作的干扰。

桌宠形象设定来自小说《诡秘之主》的主角 **克莱恩·莫雷蒂（Klein Moretti）**。在本项目中，克莱恩被表现为一只戴着黑礼帽的小黑猫，具有以下视觉特征：

- 黑色猫猫主体；
- 黑色礼帽；
- 白色衬衫领；
- 黑曜石吊坠；
- 神秘、优雅、轻量化、有桌面陪伴感。

项目强调“无感常驻”和“异步响应”。桌宠默认处于待机状态，仅在用户交互、系统状态变化或任务完成时触发反馈。所有可能造成卡顿的任务，例如大模型 API 请求、系统状态检测、全屏窗口检测等，都必须避免阻塞主界面线程。

---

## 3. 当前资产状态

### 3.1 资产已完成处理

当前三组视频资产已经经过背景抠图与裁剪处理，结果为 **1:1 正方形透明 PNG 序列帧**。这些 PNG 帧已经去除了原始视频中的纯黑背景，并裁剪掉了上下多余空白和右下角水印。

Codex 后续开发时不需要再实现视频抠图逻辑，只需要直接加载 PNG 序列帧并播放动画。

### 3.2 默认资产路径

当前资产位于：

```text
C:\Users\admin\Desktop\pet\idle
C:\Users\admin\Desktop\pet\interact
C:\Users\admin\Desktop\pet\scroll
```

每个目录内文件名规则为：

```text
frame_0000.png
frame_0001.png
frame_0002.png
...
```

三组动画含义如下：

| 动画目录 | 状态名 | 用途 |
|---|---|---|
| `idle` | `Idle` | 默认待机动画，例如呼吸、眨眼 |
| `interact` | `Interact` | 双击占卜、完成任务、用户互动 |
| `scroll` | `Scroll` | 鼠标滚轮调节亮度时的短暂反馈 |

### 3.3 路径处理要求

推荐将 `C:\Users\admin\Desktop\pet` 作为项目根目录。项目启动后，应通过 `config.json` 读取动画目录，并使用 `pathlib.Path` 拼接路径。

默认目录可以写成相对路径：

```json
{
  "animation_dirs": {
    "idle": "idle",
    "interact": "interact",
    "scroll": "scroll"
  }
}
```

这样项目根目录为 `C:\Users\admin\Desktop\pet` 时，程序会自动读取：

```text
C:\Users\admin\Desktop\pet\idle
C:\Users\admin\Desktop\pet\interact
C:\Users\admin\Desktop\pet\scroll
```

不要在代码中强行写死绝对路径。若必须支持绝对路径，也应通过 `config.json` 配置。

---

## 4. 核心技术栈

| 技术 / 库 | 作用 |
|---|---|
| Python 3.10+ | 项目主语言 |
| PyQt6 | 桌面 GUI、透明窗口、动画播放、事件监听 |
| QTimer | 播放 PNG 序列帧动画、低频 UI 刷新 |
| QPixmap | 加载透明 PNG 帧并绘制到 QLabel |
| QThread / Signal | 后台执行大模型请求与耗时任务 |
| psutil | 监控上传 / 下载网速 |
| screen_brightness_control | 滚轮调节屏幕亮度 |
| pywin32 | Windows 前台窗口检测、全屏检测 |
| openai SDK | 调用 OpenAI-compatible 大模型服务 |

推荐 `requirements.txt`：

```text
PyQt6>=6.6.0
psutil>=5.9.0
screen-brightness-control>=0.22.0
pywin32>=306; platform_system == "Windows"
openai>=1.0.0
```

---

## 5. 更新后的项目结构

由于当前动画资产已经位于项目根目录下的 `idle / interact / scroll` 文件夹中，因此推荐使用以下结构：

```text
C:\Users\admin\Desktop\pet\
│
├── main.py
├── config.json
├── requirements.txt
│
├── idle\
│   ├── frame_0000.png
│   ├── frame_0001.png
│   └── ...
│
├── interact\
│   ├── frame_0000.png
│   ├── frame_0001.png
│   └── ...
│
├── scroll\
│   ├── frame_0000.png
│   ├── frame_0001.png
│   └── ...
│
└── modules\
    ├── __init__.py
    ├── window.py
    ├── monitor.py
    ├── panel.py
    └── llm_worker.py
```

模块职责如下：

| 模块 | 主要职责 |
|---|---|
| `main.py` | 初始化 QApplication，加载配置，创建主窗口 |
| `config.json` | 保存 API、模型、动画路径、缩放、开关和缓存配置 |
| `modules/window.py` | 桌宠主窗口、透明绘制、动画状态机、拖拽、双击、滚轮、右键菜单 |
| `modules/monitor.py` | 网速监控、全屏检测、系统状态采样 |
| `modules/panel.py` | Todo List 面板、任务添加、任务完成交互 |
| `modules/llm_worker.py` | QThread 异步大模型请求、JSON 解析与兜底 |

说明：旧文档中出现的 `assets/idle.gif`、`assets/interact.gif`、`assets/scroll.gif` 已废弃。本项目当前以 PNG 序列帧为标准资产格式。

---

## 6. 配置文件设计

`config.json` 负责存储用户配置、动画路径和模型调用参数。建议第一版使用如下结构：

```json
{
  "api_key": "",
  "base_url": "",
  "model": "",
  "scale": 1.0,
  "base_size": 200,
  "animation_fps": 12,
  "animation_dirs": {
    "idle": "idle",
    "interact": "interact",
    "scroll": "scroll"
  },
  "show_network_speed": true,
  "todo_panel_visible": false,
  "last_fortune_date": "",
  "last_fortune_result": null
}
```

字段说明：

| 字段 | 说明 |
|---|---|
| `api_key` | 大模型 API Key，不要硬编码到代码中 |
| `base_url` | OpenAI-compatible 服务地址 |
| `model` | 模型名称 |
| `scale` | 桌宠整体缩放比例，初期可固定为 `1.0` |
| `base_size` | 猫猫基础视窗尺寸，默认 `200` |
| `animation_fps` | PNG 序列帧播放帧率，默认 `12` |
| `animation_dirs` | 三组动画帧目录 |
| `show_network_speed` | 是否显示网速 |
| `todo_panel_visible` | 是否默认显示 Todo 面板 |
| `last_fortune_date` | 上次占卜日期 |
| `last_fortune_result` | 当天占卜缓存 |

注意：第一阶段可以先忽略 `scale` 菜单功能，但必须从一开始保证三组动画的显示区域一致。

---

## 7. 窗口与外观设计

### 7.1 主窗口属性

桌宠主窗口应使用以下 Qt 属性：

- `Qt.WindowType.FramelessWindowHint`：无边框；
- `Qt.WindowType.WindowStaysOnTopHint`：窗口置顶；
- `Qt.WindowType.Tool`：尽量避免出现在任务栏；
- `Qt.WidgetAttribute.WA_TranslucentBackground`：窗口透明背景；
- `setAutoFillBackground(False)`：避免绘制默认矩形背景。

主窗口中建议使用一个 `QLabel` 专门显示猫猫帧图像。

### 7.2 尺寸锁定

猫猫基础视窗大小锁定为：

```python
BASE_SIZE = 200
```

每一帧都必须通过以下方式缩放：

```python
pixmap.scaled(
    200,
    200,
    Qt.AspectRatioMode.KeepAspectRatio,
    Qt.TransformationMode.SmoothTransformation
)
```

如果后续实现 0.5x / 1.0x / 1.5x 缩放，推荐逻辑是：

```python
target_size = int(base_size * scale)
```

但无论处于 `Idle`、`Interact` 还是 `Scroll` 状态，三组动画都必须使用同一个 `target_size`。不能因为某一组 PNG 原始尺寸不同，就导致桌宠在切换动画时忽大忽小。

### 7.3 窗口大小策略

第一阶段建议直接锁定：

```python
self.setFixedSize(200, 200)
self.sprite_label.setFixedSize(200, 200)
```

后续加入对白气泡和网速文本后，可以让外层窗口高度略大于 200，但猫猫 `sprite_label` 的显示区域仍应保持固定。例如：

```text
主窗口总高度 = 猫猫视窗 200 + 气泡/网速区域若干像素
猫猫 QLabel = 始终 200 x 200
```

---

## 8. 动画系统设计

### 8.1 必须使用 PNG 序列帧

禁止使用：

```python
QMovie(...)
```

必须使用：

```python
QTimer + QPixmap
```

推荐实现方式：

1. 启动时扫描对应目录中的 `frame_*.png`；
2. 使用自然顺序排序；
3. 对每张图片创建 `QPixmap`；
4. 播放时由 `QTimer` 按固定间隔切换当前帧；
5. 当前帧绘制到 `QLabel`；
6. 短动画播放完一轮后回到 `Idle`。

### 8.2 动画状态机

需要支持三个状态：

```python
class AnimationState:
    IDLE = "idle"
    INTERACT = "interact"
    SCROLL = "scroll"
```

状态行为：

| 状态 | 是否循环 | 结束后行为 |
|---|---|---|
| `Idle` | 是 | 永远循环 |
| `Interact` | 否 | 播放一轮后回到 `Idle` |
| `Scroll` | 否 | 播放一轮后回到 `Idle` |

当短动画正在播放时，如果用户再次触发滚轮或双击，可以采用以下简单策略：

- `Interact` 优先级高于 `Scroll`；
- 新的 `Interact` 可以打断 `Scroll`；
- `Scroll` 不建议打断正在播放的 `Interact`；
- 所有状态切换都不允许改变 QLabel 尺寸。

### 8.3 帧加载兜底

若某个动画目录不存在或没有任何 PNG 帧，程序不应崩溃。建议：

- 控制台打印警告；
- 对缺失的 `interact` 或 `scroll` 回退到 `idle`；
- 如果 `idle` 也缺失，则显示一个透明占位窗口，并给出错误提示。

---

## 9. 用户交互设计

### 9.1 左键拖拽移动

实现要求：

- 鼠标左键按下时记录鼠标相对窗口的位置；
- 鼠标移动时调用 `move()`；
- 鼠标释放时结束拖拽；
- 拖拽过程中不影响动画计时器。

### 9.2 双击触发赛博今日运势

双击桌宠时触发：

1. 切换到 `Interact` 动画；
2. 调用本地“今日运势”逻辑；
3. 如果大模型配置完整，则通过 `QThread` 请求克莱恩风格单句；
4. 如果未配置模型或请求失败，则显示本地兜底台词；
5. 每天第一次双击抽取新运势，当天后续双击优先复用缓存。

### 9.3 右键菜单

第一阶段至少提供：

| 菜单项 | 功能 |
|---|---|
| `退出` | 关闭程序 |

后续阶段扩展：

| 菜单项 | 功能 |
|---|---|
| `显示 / 隐藏网速` | 控制实时网速文本 |
| `每日计划` | 打开或关闭 Todo List 面板 |
| `缩放 0.5x` | 缩小桌宠 |
| `缩放 1.0x` | 恢复默认大小 |
| `缩放 1.5x` | 放大桌宠 |
| `退出` | 关闭程序 |

### 9.4 鼠标滚轮调节亮度

当鼠标悬停在桌宠窗口上时：

- 向上滚动：提高屏幕亮度；
- 向下滚动：降低屏幕亮度；
- 使用 `screen_brightness_control` 修改亮度；
- 亮度应限制在 `0` 到 `100`；
- 调节时切换到 `Scroll` 动画；
- 若亮度库不可用，应捕获异常，不允许程序崩溃。

---

## 10. 网速监控与全屏检测

### 10.1 实时网速

使用 `psutil.net_io_counters()` 获取系统网络 I/O：

1. 保存上一秒的 `bytes_sent` 和 `bytes_recv`；
2. 每秒读取一次当前值；
3. 两次差值即为上传 / 下载速度；
4. 自动格式化为 `KB/s` 或 `MB/s`；
5. 通过 Qt Signal 把结果传给窗口显示。

### 10.2 全屏自动隐藏

使用 `pywin32` 检测当前前台窗口：

1. 获取当前前台窗口句柄；
2. 排除桌宠自身窗口；
3. 获取前台窗口矩形；
4. 获取屏幕分辨率；
5. 如果前台窗口尺寸基本等于屏幕尺寸，则判断为全屏；
6. 全屏时调用 `hide()`；
7. 退出全屏时调用 `show()`。

注意事项：

- 不能让桌宠误判自己为全屏窗口；
- 全屏检测频率建议为 `1000ms` 到 `1500ms`；
- Windows API 调用必须加异常保护；
- 如果 `pywin32` 不可用，应关闭该功能而不是让程序退出。

### 10.3 线程策略

网速监控和全屏检测可以放在 `modules/monitor.py` 中统一实现。为了保持主线程稳定，推荐使用 `QObject + QThread`，由后台线程定时采样，再通过 Signal 传回主线程。

若第一版为了快速验证，也可以先用主线程 `QTimer` 做低频采样，但最终版本应优先使用独立监控线程。

---

## 11. Todo List 面板

`modules/panel.py` 负责实现半透明每日计划面板。

### 11.1 基础功能

Todo 面板需要支持：

- 添加任务；
- 显示任务列表；
- 双击任务标记完成；
- 完成任务后文字变灰并加删除线；
- 关闭 / 打开面板；
- 面板尽量保持半透明和轻量化。

### 11.2 与桌宠联动

当任务完成时：

1. 面板发出 `task_completed` Signal；
2. 主窗口接收信号；
3. 主窗口切换到 `Interact` 动画；
4. 可选：调用大模型生成一句克莱恩风格鼓励或吐槽；
5. 对白气泡短暂显示后自动消失。

---

## 12. 大模型交互层

### 12.1 线程安全要求

所有大模型请求必须通过 `QThread` 异步执行。

禁止在 `mouseDoubleClickEvent()`、`wheelEvent()`、按钮点击回调、菜单回调等主线程事件中直接请求 API。

推荐模块：

```text
modules/llm_worker.py
```

推荐模式：

```text
主线程创建任务
    ↓
LLMWorker 在 QThread 中请求 API
    ↓
worker 解析 JSON
    ↓
通过 Signal 返回 dialogue
    ↓
主线程显示对白气泡
```

### 12.2 API 配置

使用 OpenAI SDK 的 OpenAI-compatible 调用方式。不要在代码里写死 Key。

配置项来自：

```json
{
  "api_key": "",
  "base_url": "",
  "model": ""
}
```

如果 `api_key`、`base_url` 或 `model` 任一为空，应跳过 API 请求并使用本地兜底台词。

### 12.3 大模型角色提示词

系统提示词建议为：

```text
你现在是小说《诡秘之主》的主角克莱恩·莫雷蒂。
你变成了一只戴着黑礼帽的小黑猫，常驻在主人的桌面上。
你冷静、优雅、克制，但内心很会吐槽。
你可以使用“唔...”“赞美愚者”等口吻。
你只能输出 JSON，不要输出 Markdown、解释、前后缀或额外字段。
JSON 格式必须是 {"dialogue": "台词"}。
台词必须是中文，且不超过 25 个汉字。
```

### 12.4 返回格式

大模型必须返回：

```json
{
  "dialogue": "唔，今天不宜提交冒险代码。"
}
```

本地代码必须二次校验：

- 返回内容是合法 JSON；
- 存在 `dialogue` 字段；
- `dialogue` 是字符串；
- 字符数不超过 25；
- 若异常，使用本地兜底台词。

兜底台词示例：

```text
赞美愚者，接口似乎迷路了。
唔，命运暂时保持沉默。
这很合理，也很神秘。
```

---

## 13. 赛博今日运势逻辑

“赛博今日运势”采用 **本地随机抽签 + 大模型短句润色** 的方式。

### 13.1 本地抽签数据

本地维护一个运势素材列表，每条数据包含：

- 牌面；
- 正位 / 逆位；
- 今日宜；
- 今日忌；
- 幸运摸鱼时间。

示例：

```python
{
    "card": "倒吊人",
    "orientation": "逆位",
    "good": "摸鱼",
    "bad": "轻易交付代码",
    "lucky_time": "15:30"
}
```

### 13.2 触发流程

用户双击桌宠：

1. 判断 `config.json` 中的 `last_fortune_date` 是否为今天；
2. 如果是今天，读取 `last_fortune_result`；
3. 如果不是今天，本地随机抽取一条运势并写入配置；
4. 播放 `Interact` 动画；
5. 将运势文本发送给大模型；
6. 接收 `{"dialogue": "..."}`；
7. 在对白气泡中显示；
8. 若大模型不可用，则显示本地兜底对白。

### 13.3 模型输入示例

```text
主人抽到了倒吊人逆位，今天宜摸鱼，忌轻易交付代码，幸运摸鱼时间是15:30。请对此占卜进行克莱恩式单句包装。
```

### 13.4 模型输出示例

```json
{
  "dialogue": "唔，今天交付代码并不理智。"
}
```

---

## 14. 开发节奏与 Codex 输出规则

### 14.1 总体原则

Codex 不能一次性输出整个项目的所有代码。应按可运行、可验证、可回滚的方式逐步开发。

每一步都应满足：

1. 只输出当前阶段需要新增或修改的文件；
2. 每个文件都给出完整代码；
3. 说明如何运行；
4. 说明当前阶段的验收标准；
5. 不要把所有文件塞进一个超大代码块。

### 14.2 推荐开发阶段

#### 阶段 0：项目脚手架

目标：建立最小目录和配置。

建议输出：

```text
requirements.txt
config.json
modules/__init__.py
```

验收标准：

- 依赖清晰；
- 配置文件包含动画路径；
- 不涉及复杂功能。

#### 阶段 1：猫猫能显示、能动、能拖拽

目标：先把透明 PNG 序列帧小猫画到桌面上。

建议输出：

```text
main.py
modules/window.py
```

必须实现：

- PyQt6 透明无边框窗口；
- 置顶；
- 加载 `idle` PNG 序列帧；
- 使用 `QTimer + QPixmap` 播放动画；
- 每帧使用 `.scaled(200, 200, KeepAspectRatio, SmoothTransformation)`；
- 左键拖拽；
- 右键菜单至少能退出；
- 双击时播放 `interact` 一轮后回到 `idle`；
- 滚轮时播放 `scroll` 一轮后回到 `idle`；
- 若某个动画目录缺失，要有兜底逻辑。

验收标准：

- 运行 `python main.py` 后，桌面出现透明背景小猫；
- 小猫待机动画正常循环；
- 拖拽不卡顿；
- 双击和滚轮不会导致小猫大小变化；
- 右键退出可用。

#### 阶段 2：系统监控与亮度控制

目标：增加网速监控、全屏自动隐藏、滚轮亮度调节。

建议输出：

```text
modules/monitor.py
modules/window.py
config.json
```

必须实现：

- 每秒网速计算；
- 网速显示开关；
- pywin32 全屏检测；
- 全屏时隐藏桌宠，退出全屏后恢复；
- 滚轮通过 `screen_brightness_control` 调节亮度；
- 所有系统调用都要异常保护。

验收标准：

- 能看到上传 / 下载速度；
- 全屏应用出现时桌宠自动隐藏；
- 退出全屏后桌宠恢复；
- 滚轮调节亮度失败时程序不崩溃。

#### 阶段 3：Todo 面板

目标：增加每日计划功能。

建议输出：

```text
modules/panel.py
modules/window.py
config.json
```

必须实现：

- 右键菜单打开 / 关闭 Todo 面板；
- 添加任务；
- 双击任务标记完成；
- 完成任务文字变灰并加删除线；
- 完成任务触发 `Interact` 动画。

验收标准：

- 面板可以独立显示和关闭；
- 任务可添加、完成；
- 完成任务会触发猫猫互动动画。

#### 阶段 4：大模型异步对白

目标：给桌宠注入“克莱恩式短句”。

建议输出：

```text
modules/llm_worker.py
modules/window.py
config.json
```

必须实现：

- `QThread` 异步 API 请求；
- OpenAI-compatible 配置；
- JSON Mode 或 JSON 格式约束；
- 本地 JSON 校验；
- 异常兜底；
- 双击占卜触发短句；
- Todo 完成可触发短句。

验收标准：

- 大模型请求期间动画不卡顿；
- 返回 JSON 后能显示对白；
- API 配置为空时使用本地兜底；
- 非法 JSON 不会导致程序崩溃。

#### 阶段 5：体验优化与打包

目标：提高稳定性并准备分发。

建议完成：

- 配置持久化；
- 启动位置记忆；
- 错误日志；
- 图标；
- PyInstaller 打包；
- Windows 开机自启动可选项。

---

## 15. 代码质量要求

Codex 写代码时必须遵守以下要求：

1. 使用 `pathlib.Path` 处理路径；
2. 不要硬编码 API Key；
3. 不要硬编码绝对动画路径，默认从 `config.json` 读取；
4. 对系统库调用加 `try / except`；
5. 对缺失资源加友好报错；
6. 主线程只做 UI 和轻量事件处理；
7. 大模型请求必须走 QThread；
8. 动画切换不得改变 QLabel 尺寸；
9. 所有状态名使用统一常量，避免散落字符串；
10. 每一步代码都必须可以独立运行验证。

---

## 16. 给 Codex 的首轮开发提示词

第一轮只要求 Codex 实现最小可运行版本，不要让它一次写完全部功能。

可直接发送给 Codex：

```text
请根据《Klein Cat Desktop Pet — Codex 开发规格说明 v0.2》开始第一阶段开发。

当前项目根目录是：
C:\Users\admin\Desktop\pet

已有 PNG 序列帧目录：
C:\Users\admin\Desktop\pet\idle
C:\Users\admin\Desktop\pet\interact
C:\Users\admin\Desktop\pet\scroll

文件名均为 frame_0000.png、frame_0001.png ...

请先只输出以下文件：
1. main.py
2. modules/window.py

要求：
- 使用 PyQt6；
- 使用透明、无边框、置顶窗口；
- 使用 QTimer + QPixmap 播放 PNG 序列帧；
- 不要使用 QMovie；
- 每一帧必须 scaled(200, 200, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)；
- 三组动画切换时保持 200x200 视窗尺寸完全一致；
- idle 动画循环播放；
- 双击播放 interact 一轮后回到 idle；
- 鼠标滚轮播放 scroll 一轮后回到 idle；
- 左键拖拽移动窗口；
- 右键菜单至少包含“退出”；
- 如果 interact 或 scroll 资源缺失，回退到 idle；
- 如果 idle 资源缺失，程序要给出清晰错误信息而不是崩溃。

请不要输出 monitor.py、panel.py、llm_worker.py，这些放到后续阶段再开发。
每个文件单独用代码块输出，并在最后说明如何运行和如何验收。
```

---

## 17. 关键矛盾修正说明

本文档对原始说明进行了以下修正：

| 原始/旧表述 | 修正后 |
|---|---|
| 使用 `idle.gif / interact.gif / scroll.gif` | 使用 `idle / interact / scroll` 三个 PNG 序列帧目录 |
| 使用 `QMovie` 播放动画 | 使用 `QTimer + QPixmap` 播放 PNG 帧 |
| 资产放在 `assets/*.gif` | 当前默认资产位于项目根目录下的 `idle / interact / scroll` |
| 缩放功能可能导致三组动画尺寸不一致 | 所有动画状态共享同一个 `base_size / target_size` |
| 一次性生成全部核心代码 | 改为分阶段开发，先实现主窗口和动画，再逐步增加功能 |
| 大模型请求可能在 UI 事件中直接执行 | 强制使用 `QThread` 异步请求，通过 Signal 回传结果 |

---

## 18. 最终验收清单

项目完成后应满足：

1. 桌面出现透明背景克莱恩小黑猫；
2. 待机动画持续循环；
3. 双击、滚轮、完成任务能触发对应动画；
4. 三组动画切换时猫猫尺寸不跳变；
5. 左键可以拖拽；
6. 右键可以打开菜单；
7. 网速显示可开关；
8. Todo 面板可添加和完成任务；
9. 全屏应用时桌宠自动隐藏；
10. 退出全屏后桌宠恢复；
11. 滚轮可以调节亮度；
12. 大模型请求不阻塞动画；
13. 大模型返回内容必须是 `{"dialogue": "..."}`；
14. API 不可用时有本地兜底；
15. 配置能持久化保存；
16. 代码可读、模块清晰、易于继续扩展。

---

## 19. 一句话总结

**Klein Cat 是一个基于 PyQt6 的轻量化克莱恩小黑猫桌宠。当前版本应以透明 PNG 序列帧为核心动画资产，通过 `QTimer + QPixmap` 播放，并按“先显示猫猫，再接入监控和面板，最后接入大模型灵魂”的节奏逐步开发。**
