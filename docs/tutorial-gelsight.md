# GelSight / DIGIT 传感器标注教程

本教程演示如何为 GelSight Mini 或 DIGIT 触觉传感器的数据添加标注。

## 前置准备

```bash
pip install tlabel[gelsight]
```

这会安装 `opencv-python`，用于处理触觉图像。

## 步骤 1: 准备数据

GelSight/DIGIT 的数据通常是 `.pkl` 文件，包含以下字段：
- `trajectory`: 触觉图像序列 (N, 240, 320, 3) RGB 数组
- `contact`: 接触标签 (可选)
- `slip`: 滑移标签 (可选)
- `forces`: 力估计向量 (可选)

如果你的数据格式不同，适配器会尝试自动适配。

## 步骤 2: 加载数据

```python
import tlabel

# 加载你的 .pkl 文件
data = tlabel.load("my_gelsight_episode.pkl")

print(f"加载了 {data.num_frames} 帧")
print(f"传感器类型: {data.sensor_type}")
```

**发生了什么：**
1. 适配器读取 pickle 文件
2. 对每帧 tactile 图像做背景减除（随机采样 50-100 帧计算中值背景）
3. 从背景减除后的图像提取 22 维特征：
   - 接触检测、力度大小、力度方向
   - 滑移检测、滑移熵
   - 光流（Farneback 算法）
   - 法向场/剪切场
   - 纹理能量、边缘密度等
4. 用状态机推断操作阶段（idle → initial_contact → stable_contact → slip → release）

## 步骤 3: 查看和修正标注

```python
# 在 Jupyter Notebook 中打开交互面板
data.review()
```

面板功能：
- **时间线**: 绿色=接触，红色=滑移，灰色=空闲
- **雷达图**: 22 维特征的可视化
- **批量修正**: 选择一段帧范围，统一修改某个字段

**常见问题及修正方法：**

| 问题 | 表现 | 修正方法 |
|------|------|----------|
| 接触误判 | 没接触时 contact=1 | 选中这些帧，设 contact=0，cascade 会自动清零 force/slip |
| 滑移漏检 | 明显滑动但 slip_event=0 | 手动设 slip_event=1 |
| 力度异常 | force_magnitude > 1 或 < 0 | 检查原始力估计是否归一化，手动修正 |

## 步骤 4: 导出标注

```python
# 导出为 JSON（完整 TLabel Format v2）
data.export("gelsight_annotated.json")

# 导出为 CSV（方便 pandas/Excel 分析）
data.export("gelsight_annotated.csv")
```

JSON 输出示例：
```json
{
  "schema_version": "0.4.0",
  "sensor_info": {
    "type": "vision_based_tactile",
    "model": "GelSight Mini"
  },
  "capabilities": {
    "contact": true,
    "force_magnitude": true,
    "optical_flow_magnitude": true,
    ...
  },
  "episodes": [
    {
      "episode_id": "episode_0",
      "frames": [
        {
          "frame_idx": 0,
          "timestamp_s": 0.0,
          "contact": 0.0,
          "force_magnitude": 0.0,
          "slip_event": 0.0,
          "manipulation_phase": "idle",
          ...
        }
      ]
    }
  ]
}
```

## 进阶技巧

### 处理多个 trajectory

如果 `.pkl` 文件包含多个 trajectory（如 Facebook gelsight-force-estimation 数据集）：

```python
# 先查看有哪些 trajectory
import pickle
with open("multi_traj.pkl", "rb") as f:
    data_dict = pickle.load(f)
print(data_dict.keys())  # 查看可用的 key

# 加载时指定 trajectory_id
data = tlabel.load("multi_traj.pkl", trajectory_id=0)
```

### 编程式批量修正

```python
# 将第 10-50 帧的 contact 设为 0
data.batch_patch(10, 50, "contact", 0)

# 将第 60-80 帧的 slip_event 设为 1
data.batch_patch(60, 80, "slip_event", 1)
```

### 检查标注质量

```python
# 查看有多少帧被手动修正过
print(f"修正过的帧数: {data.modified_count}")

# 检查物理一致性（contact=0 但 force>0 的矛盾帧）
for i in range(data.num_frames):
    frame = data[i]
    if frame.contact == 0 and frame.force_magnitude > 0.1:
        print(f"帧 {i}: contact=0 但 force={frame.force_magnitude:.3f}")
```

## 常见问题

### Q: 光流计算很慢怎么办？

A: 光流（Farneback）确实比较耗时。如果不需要 temporal 特征，可以跳过：
```python
# 目前适配器总是计算光流，未来版本会加开关
# 临时方案：导出后手动删除 optical_flow 相关字段
```

### Q: 背景减除效果不好怎么办？

A: 背景减除假设前几帧是"无接触"状态。如果数据开头就有接触，背景会被污染。解决方法：
1. 确保数据采集时开头有几帧空闲状态
2. 或者手动指定背景帧范围（未来版本支持）

### Q: 我的 GelSight 变种传感器不支持怎么办？

A: 如果传感器输出格式与标准 GelSight 不同，可以：
1. 自己写一个适配器继承 `BaseAdapter`
2. 或者先用脚本把数据转换成标准 `.pkl` 格式
3. 联系我们添加官方支持

---

[返回 README](../README.md) | [PaXini 教程](tutorial-paxini.md) | [Daimon 教程](tutorial-daimon.md)
