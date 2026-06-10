# TouchLabel AI 🦞

<h3 align="center">传感器无关的触觉数据标注工具</h3>
<p align="center"><strong>load → review → export · 三步闭环</strong></p>

<p align="center">
  <a href="https://pypi.org/project/tlabel/"><img src="https://img.shields.io/pypi/v/tlabel?color=e85d75" alt="PyPI"></a>
  <a href="https://pypi.org/project/tlabel/"><img src="https://img.shields.io/pypi/pyversions/tlabel" alt="Python"></a>
  <a href="https://github.com/liesliy/tlabel/blob/main/LICENSE"><img src="https://img.shields.io/pypi/l/tlabel" alt="License"></a>
  <a href="https://github.com/liesliy/tlabel/stargazers"><img src="https://img.shields.io/github/stars/liesliy/tlabel?style=social" alt="GitHub Stars"></a>
  <a href="https://pepy.tech/projects/tlabel"><img src="https://img.shields.io/pepy/dt/tlabel?color=blue" alt="Downloads"></a>
  <a href="README.md">English</a>
</p>

---

> 🎯 **不同传感器的触觉数据互相看不懂？**
> TLabel 让它们说同一种语言——加载任意格式，可视化标注，导出统一标准。

---

## ⚡ 30秒体验

没有数据？无所谓。Jupyter里跑这几行：

```python
import tlabel
data = tlabel.demo()    # ← 内置GelSight演示数据
data.review()           # ← 交互面板直接弹出来
```

换个传感器试试：

```python
tlabel.demo('digit').review()    # DIGIT
tlabel.demo('paxini').review()   # 帕西尼力觉传感器
tlabel.demo('daimon').review()   # 戴盟DM-TacClaw
```

**你会看到：** 彩色时间轴（🟢接触 / 🔴滑移 / ⬜空闲）、22维雷达图、帧详情编辑器、批量修正——一个面板全搞定。

![TouchLabel AI 面板演示](docs/demo_panel.gif)

---

## 🚀 快速上手

```bash
pip install tlabel
```

```python
import tlabel

# 加载 — 自动识别传感器格式，不用你操心
data = tlabel.load("gelsight_force.pkl")     # GelSight / DIGIT
data = tlabel.load("paxini_episode.h5")      # 帕西尼
data = tlabel.load("daimon_data/")           # 戴盟（目录或 .parquet）

# 标注 — Jupyter交互面板
data.review()          # 中文界面
data.review(lang="en") # 英文界面

# 导出 — 统一TLabel格式
data.export("output.json")   # TLabel Format v2 JSON
data.export("output.csv")    # CSV平面表
```

就这样。三行代码，完整闭环。🔁

---

## 🤔 为什么要用TLabel？

| 痛点 | TLabel怎么解决 |
|------|---------------|
| 每个传感器导出的格式都不一样 | **一个`load()`调用，自动识别** |
| 原始触觉数据就是一堆数字，看不懂 | **可视化面板：时间轴+雷达图+帧详情** |
| 逐帧改标注改到怀疑人生 | **批量修正+联动规则，一键改一段** |
| 实验室小伙伴导出的东西……不敢问 | **统一TLabel Format v2，22维标准，没有歧义** |
| "我们用DIGIT，他们用帕西尼" | **传感器无关。两种都加载，同一套标准，同一工具** |

---

## 📡 支持的传感器

| 传感器 | 格式 | 维度 | 光流 | 状态 |
|--------|------|:----:|:----:|:----:|
| **GelSight Mini** | `.pkl` | 22 | ✅ | ✅ 稳定 |
| **DIGIT** | `.pkl` | 22 | ✅ | ✅ 稳定 |
| **戴盟 DM-TacClaw** | `.parquet` / 目录 | 22（有视频）/ 20（无视频） | ✅ / — | ✅ 稳定 |
| **帕西尼 PXCap** | `.h5` / `.hdf5` | 20 | — | ✅ 稳定 |

> 力觉型传感器（帕西尼）没有光学图像→20维；图像型→完整22维；戴盟在没有视频文件时自动降级到20维。不会报错，不会出幺蛾子。

---

## 📦 安装

```bash
# 只要核心（只要numpy，装两秒）
pip install tlabel

# 按传感器装依赖
pip install tlabel[gelsight]   # GelSight / DIGIT → opencv-python
pip install tlabel[paxini]     # 帕西尼 → h5py
pip install tlabel[daimon]     # 戴盟 → pyarrow + opencv-python

# 我全都要
pip install tlabel[all]
```

---

## 🎨 面板功能

- 🎨 **彩色时间轴**：绿=接触 · 红=滑移 · 灰=空闲，模式一眼就看出来
- 🕸 **22维雷达图**：完整特征向量一览，中英双语标签
- ✏️ **帧修正 & 批量修正**：改一帧还是改一串，你说了算
- 🔗 **联动规则**：`contact`设为0 → 7个关联字段自动归零 + 阶段重置为`idle`
- 🌐 **中英文切换**：右上角一键切换
- 📤 **导出**：JSON / CSV，后缀名自动识别

---

## TLabel Format v2 — 22个维度

### 静态特征（18维）

| # | 字段 | 说明 |
|---|------|------|
| 1 | `contact` | 接触标志（0/1） |
| 2 | `deformation_magnitude` | 表面形变强度 |
| 3 | `force_magnitude` | 法向力大小 |
| 4 | `force_peak` | 窗口内峰值力 |
| 5 | `force_direction` | 力向量角度（°） |
| 6 | `slip_entropy` | 滑移检测不确定性 |
| 7 | `slip_event` | 滑移事件标志（0/1） |
| 8 | `texture_energy` | 纹理频率能量 |
| 9 | `edge_density` | 接触边缘像素比 |
| 10 | `contact_area` | 接触区域面积比 |
| 11 | `centroid_x` | 接触质心x坐标 |
| 12 | `normal_field_magnitude` | 法向压力场强度 |
| 13 | `normal_field_variance` | 法向场空间方差 |
| 14 | `shear_field_magnitude` | 剪切力强度 |
| 15 | `shear_field_direction` | 剪切力方向角（°） |
| 16 | `delta_force_normal` | 帧间ΔF_normal |
| 17 | `delta_force_shear` | 帧间ΔF_shear |
| 18 | `friction_cone_ratio` | 切向/法向力比 |

### 时序特征（4维，v0.2.0新增）

| # | 字段 | 图像型 | 力觉型 | 说明 |
|---|------|:------:|:------:|------|
| 19 | `optical_flow_magnitude` | ✅ | — | 帧间运动幅度（Farneback） |
| 20 | `optical_flow_direction` | ✅ | — | 光流方向角（°） |
| 21 | `temporal_deformation_rate` | ✅ | ✅ | 形变变化率 |
| 22 | `contact_transition` | ✅ | ✅ | 接触状态转移概率 |

---

## 📖 API速查

```python
import tlabel

# ── 加载 ──
data = tlabel.load(path)                     # 自动识别传感器格式
data = tlabel.load(path, format="gelsight")  # 指定适配器

# ── Demo ──
data = tlabel.demo()                         # 内置演示数据
tlabel.list_demos()                          # 查看可用的传感器

# ── 属性 ──
data.num_frames        # 总帧数
data.duration_s        # 时长（秒）
data.sensor_type       # 传感器标识
data.dimension_keys    # 所有维度字段名
data.modified_count    # 已手动修正的帧数

# ── 帧访问 ──
frame = data[0]                          # 按索引
frame = data.get_frame(42)               # 按frame_idx
frame.contact                            # 接触值
frame.slip_event                         # 滑移事件值
frame.is_modified                        # 是否已修正

# ── 修正 ──
frame.patch("contact", 0)                         # 单帧（联动=True）
frame.patch("contact", 0, cascade=False)           # 不联动
data.batch_patch(10, 50, "contact", 0)             # 区间批量修正

# ── 标注 & 导出 ──
data.review()                    # Jupyter面板（中文）
data.review(lang="en")           # 英文
data.export("output.json")       # JSON（TLabel Format v2）
data.export("output.csv")        # CSV
```

### 联动规则（contact → 0）

`contact`设为0时，以下字段自动归零：

| 自动归零字段 | 条件 |
|-------------|------|
| `force_magnitude` | 始终 |
| `force_peak` | 始终 |
| `slip_event` | 始终 |
| `delta_force_normal` | 始终 |
| `delta_force_shear` | 始终 |
| `contact_area` | 始终 |
| `contact_transition` | 仅当值 > 0.5 |
| `manipulation_phase` | → `"idle"`（如果还不是） |

---

## 🗂 项目结构

```
tlabel/
├── core/
│   ├── types.py          # TLabelFrame / TLabelData 容器
│   ├── loader.py         # 自动识别 & 调度加载
│   └── registry.py       # 适配器注册表
├── adapters/
│   ├── base.py           # BaseAdapter 接口
│   ├── gelsight.py       # GelSight Mini / DIGIT
│   ├── paxini.py         # 帕西尼 PXCap
│   └── daimon.py         # 戴盟 DM-TacClaw（+视频解码）
├── viewer/
│   ├── panel.py          # Jupyter _repr_html_ 渲染
│   └── templates.py      # HTML + JS + CSS 模板引擎
├── demo.py               # 内置演示数据加载器
└── export/
    └── writer.py         # JSON / CSV 导出 + NumpyEncoder
```

---

## 💬 反馈

发现问题？有想法？想聊聊天？

- 🐛 **Bug** → [提Issue](https://github.com/liesliy/tlabel/issues)
- 💡 **功能建议** → [GitHub Discussions](https://github.com/liesliy/tlabel/discussions)
- 🌟 **在研究中用了TLabel？** → 告诉我们！给个⭐也行

## 🤝 贡献

欢迎贡献！参见 [CONTRIBUTING.md](CONTRIBUTING.md)。

**适合新手上手的Issue：**
- 🔌 加一个新的传感器适配器（SynTouch？XELA？你说了算）
- 📊 改进雷达图UI（暗色模式、交互悬停）
- 🌐 加更多语言（日本語、한국어）
- 🧪 补集成测试

---

## 📄 许可证

[MIT](LICENSE) © 牛宿科技

---

<p align="center">
  <strong>如果TLabel帮你省下了手动标注触觉数据的时间，给个⭐让我们开心一下！</strong>
</p>
