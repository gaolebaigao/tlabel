# TouchLabel AI 快速上手

## 1. 安装

```bash
# 基础安装
pip install tlabel

# 按传感器装可选依赖
pip install tlabel[gelsight]   # GelSight / DIGIT → opencv-python
pip install tlabel[paxini]     # PaXini → h5py
pip install tlabel[daimon]     # Daimon → pyarrow + opencv-python

# 一步到位
pip install tlabel[all]
```

> 源码安装：`cd tlabel-pip && pip install -e .`

## 2. 试用 Demo 数据

不想找真实数据？我们准备了合成 demo：

```python
import json
from tlabel.core.types import TLabelFrame, TLabelData

# 下载 demo 数据（GelSight 150帧，22维）
# 也可以从 examples/data/demo_gelsight.json 本地加载
with open("examples/data/demo_gelsight.json") as f:
    raw = json.load(f)

frames = [
    TLabelFrame(f["frame_idx"], f["timestamp_s"], f["tlabel_v2"],
                f.get("manipulation_phase", "idle"), f.get("confidence", 1.0))
    for f in raw["frames"]
]
data = TLabelData(frames, raw["sensor"], raw["episode"], raw["capabilities"])
data.review()  # Jupyter 面板
```

可用的 demo 数据：
- `examples/data/demo_gelsight.json` — GelSight Mini 150帧，22维（含光流）
- `examples/data/demo_paxini.json` — PaXini PXCap 120帧，20维（无力觉图像）

## 3. 加载真实数据

```python
import tlabel

# 自动识别格式
data = tlabel.load("gelsight_force.pkl")     # GelSight / DIGIT
data = tlabel.load("paxini_episode.h5")      # PaXini
data = tlabel.load("daimon_data/")           # Daimon 目录或 .parquet

# 手动指定
data = tlabel.load("data.pkl", format="gelsight")
```

## 4. 标注面板

**必须在 Jupyter Notebook / JupyterLab 里用**：

```python
data.review()          # 中文
data.review(lang="en") # English
```

面板功能：
- **时间轴**：绿=接触 · 红=滑移 · 灰=无接触
- **雷达图**：22维特征分布（力觉型20维）
- **统计栏**：帧数、时长、接触率、滑移率
- 右上角**中英文切换**

## 5. 修改标注

```python
# 单帧修改
frame = data[0]
frame.patch("contact", 0)            # contact→0 自动联动清除7个关联字段
frame.patch("slip_event", 1)         # 改滑移
frame.patch("force_magnitude", 3.5)  # 改力度

# 批量修改
data.batch_patch(10, 50, "contact", 0)    # 第10-50帧接触改0
data.batch_patch(10, 50, "slip_event", 1)  # 第10-50帧滑移改1
```

### Cascade 联动规则

`contact` 设为 0 时，以下字段自动归零：
- `force_magnitude`, `force_peak`, `slip_event`
- `delta_force_normal`, `delta_force_shear`
- `contact_area`
- `contact_transition`（仅当值 > 0.5 时）
- `manipulation_phase` → `"idle"`

## 6. 导出

```python
# 后缀自动判断格式
data.export("output.json")   # JSON（TLabel Format v2）
data.export("output.csv")    # CSV 平面表

# 显式指定格式
data.export("output", format="json")
```

## 7. 常见问题

**Q: `pip install tlabel` 找不到包？**
A: 确认 Python ≥ 3.8，或用源码安装 `pip install -e .`

**Q: `No module named 'cv2'`？**
A: GelSight / DIGIT / Daimon 需要 `pip install opencv-python`

**Q: `No module named 'h5py'`？**
A: PaXini 需要 `pip install h5py`

**Q: `No module named 'pyarrow'`？**
A: Daimon 需要 `pip install pyarrow`

**Q: 面板不显示？**
A: 必须在 Jupyter 里跑，普通 Python 终端不支持 HTML 渲染

---

三步闭环：`load → review → export`，就这些 🦞
