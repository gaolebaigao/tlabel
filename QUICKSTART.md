# TouchLabel AI 快速上手

## 1. 安装

```bash
# 基础安装（只有numpy，什么传感器都能加载标注，只是缺可视化依赖）
pip install tlabel

# 按你的传感器装可选依赖
pip install tlabel[gelsight]   # GelSight / DIGIT（需要opencv）
pip install tlabel[paxini]     # 帕西尼（需要h5py）
pip install tlabel[daimon]     # 戴盟（需要pyarrow）

# 或者一步到位
pip install tlabel[all]
```

> 如果你是从源码装：`cd tlabel-pip && pip install -e .`

## 2. 加载数据

```python
import tlabel

# 自动识别格式，直接传路径就行
data = tlabel.load("gelsight_force.pkl")     # GelSight/DIGIT .pkl
data = tlabel.load("paxini_episode.h5")      # 帕西尼 .h5
data = tlabel.load("daimon_data/")           # 戴盟 目录或.parquet

# 如果自动识别不准，手动指定
data = tlabel.load("data.pkl", format="gelsight")
```

加载完会打印摘要，告诉你多少帧、接触率多少。

## 3. 看标注面板

**必须在 Jupyter Notebook 里用**（JupyterLab也行）：

```python
data.review()          # 中文界面
data.review(lang="en") # 英文界面
```

会弹出一个面板，包含：
- **时间轴**：绿=接触、红=滑移、灰=无接触
- **雷达图**：18维特征分布
- **统计栏**：帧数、时长、接触率、滑移率
- 右上角**中英文切换**

## 4. 修改标注

```python
# 单帧修改 — 传位置参数（不是keyword）
frame = data[0]
frame.patch("contact", 0)          # 改接触状态
frame.patch("slip_event", 1)       # 改滑移事件
frame.patch("force_magnitude", 3.5) # 改力度

# 联动规则：contact改成0时，force_magnitude和slip_event自动归零
# 不用你手动清，改contact就行

# 批量修改
data.batch_patch(10, 50, "contact", 0)       # 第10-50帧接触改0
data.batch_patch(10, 50, "slip_event", 1)     # 第10-50帧滑移改1
```

## 5. 导出

```python
# JSON（TLabel Format v2 完整结构）
data.export("output.json")

# CSV（平面表，方便Excel看）
data.export("output.csv")
```

## 6. 常见问题

**Q: `pip install tlabel` 找不到包？**
A: 还没发PyPI，目前只能源码装：`pip install -e .`

**Q: 加载报错 `No module named 'cv2'`？**
A: GelSight/DIGIT需要opencv：`pip install opencv-python`

**Q: 加载报错 `No module named 'h5py'`？**
A: 帕西尼需要h5py：`pip install h5py`

**Q: 加载报错 `No module named 'pyarrow'`？**
A: 戴盟需要pyarrow：`pip install pyarrow`

**Q: 面板不显示？**
A: 必须在Jupyter里跑，普通Python终端不行。

**Q: 加戴盟数据怎么传路径？**
A: 传目录路径或.parquet文件路径都行，会自动检测。

---

三步闭环：`load → review → export`，就这些 🦞
