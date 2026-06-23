# TLabel 快速上手

TLabel 是一个开源触觉数据标注工具，支持 GelSight、DIGIT、PaXini、VTouch 等多种触觉传感器格式。

## 1. 安装

```bash
# 基础安装
pip install tlabel

# 按传感器选装可选依赖
pip install tlabel[gelsight]   # GelSight / DIGIT → opencv-python
pip install tlabel[paxini]     # PaXini → h5py
pip install tlabel[vtouch]      # VTouch → h5py
pip install tlabel[all]        # 安装全部可选依赖
```

> 源码安装：`pip install -e .`

## 2. Demo 数据

TLabel 内置合成 demo，一行代码即可体验完整功能：

```python
import tlabel

# 默认 GelSight demo（150帧，22维特征）
data = tlabel.demo()

# 指定数据集
data = tlabel.demo('digit')     # DIGIT 传感器
data = tlabel.demo('paxini')    # PaXini 传感器

# 打开标注面板
data.review()
```

> **面板功能**：
> - 📝 **标注 Tab**：雷达图、时间轴、帧详情、批量修正
> - 🎬 **Episode Tab**：操作结果、操作类型、难度等级等语义标注
> - 📊 **质量评分 Tab**：4维度数据质量评估
> - 📈 **统计 Tab**：类似 pandas describe() 的统计摘要
> - 🌙 右上角 **D 键**切换暗色模式
> - 🌍 右上角 **EN 按钮**切换中英文

## 3. 加载真实数据

```python
import tlabel

# 自动识别格式（推荐）
data = tlabel.load("episode_data.h5")

# 手动指定格式
data = tlabel.load("data.h5", format='vtouch')    # VTouch HDF5
data = tlabel.load("data.h5", format='paxini')    # PaXini HDF5
data = tlabel.load("data.pkl", format='gelsight') # GelSight pickle
```

支持的格式：
| 格式 | 文件后缀 | 说明 |
|------|---------|------|
| `vtouch` | `.h5`, `.hdf5` | VTouch 触觉数据 |
| `paxini` | `.h5`, `.hdf5` | PaXini PXCap 数据 |
| `gelsight` | `.pkl`, `.json` | GelSight / DIGIT 数据 |
| `auto_detect` | 任意 | 自动检测传感器格式 |

## 4. AI 预标注

TLabel 提供基于规则的 AI 预标注功能，可加速标注流程：

```python
from tlabel.predict import PredictEngine

# 创建预测引擎
engine = PredictEngine()

# 对数据应用预测
engine.fit(data)    # 分析数据分布
engine.apply(data)  # 生成预测标签

# 查看预测摘要
engine.summary(data)
```

预标注结果会高亮显示在面板中（🤖 Predicted 徽章），支持手动修正。

## 5. 标注面板

**必须在 Jupyter Notebook / JupyterLab 中使用**：

```python
data.review()          # 中文界面
data.review(lang="en") # 英文界面
```

### 键盘快捷键

| 按键 | 功能 |
|------|------|
| `←` `→` | 切换帧 |
| `空格` | 标记/取消接触 |
| `S` | 标记/取消滑移 |
| `D` | 切换暗色模式 |
| `?` | 显示帮助 |

### 修改单帧标注

```python
frame = data[0]
frame.patch("contact", 0)            # 标记为非接触
frame.patch("contact", 1)            # 标记为接触
frame.patch("slip_event", 1)        # 标记滑移
frame.patch("force_magnitude", 3.5) # 修改力度值
```

### 批量修正

```python
# 帧范围修正
data.batch_patch(start=10, end=50, field="contact", value=0)
data.batch_patch(start=10, end=50, field="manipulation_phase", value="stable_contact")
```

### Cascade 联动规则

当 `contact` 设为 0 时，以下字段自动归零：
- `force_magnitude`, `force_peak`, `slip_event`
- `delta_force_normal`, `delta_force_shear`
- `contact_area`
- `manipulation_phase` → `"idle"`

## 6. 导出数据

### 方式一：面板按钮导出

在标注面板底部点击导出按钮：
- 💾 **导出 JSON**（主按钮）：完整 TLabel Format v2
- 📊 **导出 CSV**：扁平表格格式
- 🔬 **导出 HDF5**：需要 Python API

### 方式二：Python API 导出

```python
# 根据后缀自动判断格式
data.export("output.json")   # JSON 格式
data.export("output.csv")    # CSV 扁平表
data.export("output.hdf5")   # HDF5 科学格式

# 显式指定格式
data.export("output", format="json")
data.export("output", format="csv")
```

## 7. VTouch 数据格式

VTouch 是支持力度图像的触觉传感器格式：

```python
import tlabel

# 加载 VTouch HDF5 文件
data = tlabel.load("recording.h5", format='vtouch')

# 预览数据结构
print(data)

# 打开标注面板
data.review()
```

## 8. 统计与质量评估

### 统计摘要

```python
# 获取统计信息（类似 pandas describe()）
stats = data.describe()
print(stats)
```

### 质量评分

```python
# 计算数据质量评分
quality = data.quality_score()
print(f"综合评分: {quality['overall']}")
print(f"等级: {quality['grade']}")
```

评分维度：
- 🔧 **物理一致性**（权重 30%）：联动规则满足度
- 📈 **时序平滑度**（权重 25%）：相邻帧突变检测
- 📋 **完整性**（权重 25%）：字段缺失/全零比例
- 🎯 **覆盖率**（权重 20%）：有意义标注占比

## 常见问题

**Q: `pip install tlabel` 找不到包？**
A: 确认 Python ≥ 3.8，或使用源码安装 `pip install -e .`

**Q: `No module named 'cv2'`？**
A: GelSight / DIGIT 需要 opencv-python：`pip install tlabel[gelsight]`

**Q: `No module named 'h5py'`？**
A: PaXini / VTouch 需要 h5py：`pip install tlabel[paxini]` 或 `pip install tlabel[vtouch]`

**Q: 面板在 Jupyter 中不显示？**
A: 确保在 Jupyter Notebook/Lab 环境中运行，终端不支持 HTML 渲染

**Q: 如何导出 AI 预标注结果？**
A: 预标注会写入帧数据，导出时自动包含。面板中显示 🤖 徽章表示为预测值。

---

**三步闭环**：`tlabel.load()` → `data.review()` → `data.export()`

有任何问题欢迎提交 Issue：https://github.com/liesliy/tlabel/issues
