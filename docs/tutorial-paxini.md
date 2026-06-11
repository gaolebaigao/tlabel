# PaXini PXCap 传感器标注教程

本教程演示如何为 PaXini PXCap 分布式力阵列传感器的数据添加标注。

## 前置准备

```bash
pip install tlabel[paxini]
```

这会安装 `h5py`，用于读取 HDF5 格式数据。

## 步骤 1: 准备数据

PaXini PXCap 的数据是 `.h5` 或 `.hdf5` 文件，包含：
- **左右手触觉数据**: 每个手有多个 taxel 区域（如 thumb, index, middle 等）
- **6D 力/力矩向量**: 每个 taxel 输出 (Fx, Fy, Fz, Mx, My, Mz)
- **时间戳**: 每帧的时间戳（毫秒）

如果你的数据是原始 HDF5，适配器会自动解析。如果已经是 TLabel 格式的 JSON，也可以直接加载。

## 步骤 2: 加载数据

```python
import tlabel

# 加载你的 .h5 文件
data = tlabel.load("my_paxini_episode.h5")

print(f"加载了 {data.num_frames} 帧")
print(f"传感器类型: {data.sensor_type}")
```

**发生了什么：**
1. 适配器读取 HDF5 文件，提取左右手各 taxel 区域的力数据
2. 对每个 taxel 做基线减除（取前几帧的平均值作为 baseline）
3. 检测接触状态：当某 taxel 的力超过阈值时标记为 contact
4. 检测滑移：通过质心偏移 + 力变化率判断
5. 映射到 20 维 TLabel 特征（无力学图像，所以没有 optical_flow 和 shear_field）
6. 推断操作阶段（approach / stable_contact / slip / retract）

## 步骤 3: 查看和修正标注

```python
# 在 Jupyter Notebook 中打开交互面板
data.review()
```

**PaXini 特有的注意事项：**
- PaXini 只有 20 维（比 GelSight 少 2 维），因为没有光学图像
- `optical_flow_magnitude` 和 `optical_flow_direction` 始终为 0
- `shear_field_magnitude` 和 `shear_field_direction` 也缺失
- 滑移检测是间接推断的（通过力变化），不如视觉型传感器准确

**常见问题及修正方法：**

| 问题 | 表现 | 修正方法 |
|------|------|----------|
| 接触漏检 | 有力但 contact=0 | 检查 force_magnitude 是否超过阈值，手动设 contact=1 |
| 滑移误判 | 力变化大但不是真滑移 | PaXini 的滑移检测基于启发式规则，容易误判，需人工校验 |
| 区域命名混乱 | 不知道哪个 taxel 对应哪个手指 | 查看 sensor_specific 字段中的 region 名称 |

## 步骤 4: 导出标注

```python
# 导出为 JSON
data.export("paxini_annotated.json")

# 导出为 CSV
data.export("paxini_annotated.csv")
```

JSON 输出示例（注意 capabilities 中光学相关字段为 false）：
```json
{
  "schema_version": "0.4.0",
  "sensor_info": {
    "type": "distributed_taxel_array",
    "model": "PXCap",
    "manufacturer": "paxini"
  },
  "capabilities": {
    "contact": true,
    "force_magnitude": true,
    "slip_event": true,
    "optical_flow_magnitude": false,
    "shear_field_magnitude": false,
    ...
  },
  "episodes": [...]
}
```

## 从原始 HDF5 转换

如果你的 PaXini 数据不是标准格式，可以先用 `paxini_adapter.py` 转换：

```bash
# 找到 tlabel-web 中的 paxini-toolkit
cd tlabel-web/paxini-toolkit
python paxini_adapter.py your_raw_data.h5 --output converted.json
```

然后加载转换后的 JSON：
```python
data = tlabel.load("converted.json")
```

## 进阶技巧

### 检查多区域协调

PaXini 是多税点阵列，可以检测多个手指的协调动作：

```python
# 查看某一帧的各区域详情
frame = data[0]
print(frame.sensor_specific)
# 输出类似：
# {
#   'right_regions': {'thumb': {...}, 'index': {...}, ...},
#   'left_regions': {'thumb': {...}, 'index': {...}, ...}
# }
```

### 跨 episode 比较

```python
# 加载多个 episode
data1 = tlabel.load("episode_1.h5")
data2 = tlabel.load("episode_2.h5")

# 比较接触率
rate1 = sum(1 for f in data1 if f.contact > 0.5) / data1.num_frames
rate2 = sum(1 for f in data2 if f.contact > 0.5) / data2.num_frames
print(f"Episode 1 接触率: {rate1:.2%}")
print(f"Episode 2 接触率: {rate2:.2%}")
```

## 常见问题

### Q: PaXini 的滑移检测为什么不准？

A: PaXini 是纯力学传感器，没有视觉信息。滑移检测是通过"质心偏移 + 力变化率"间接推断的，容易受噪声影响。建议：
1. 在交互面板中仔细检查 slip_event 标记
2. 结合视频录像（如果有外部相机）人工校验
3. 未来版本会加入基于机器学习的滑移检测模型

### Q: 左右手数据如何区分？

A: 适配器会自动检测 HDF5 中的左右手数据集，并分别存储到 `sensor_specific['left_regions']` 和 `sensor_specific['right_regions']`。TLabel 主维度（20 维）是双手的聚合统计。

### Q: 我的 PaXini 变种传感器有更多/更少的 taxel 怎么办？

A: 适配器会自动适应不同数量的 taxel 区域。只要 HDF5 结构相似（有 regions/baseline 等字段），应该能正常工作。如果格式差异大，请联系作者添加支持。

---

[返回 README](../README.md) | [GelSight 教程](tutorial-gelsight.md) | [Daimon 教程](tutorial-daimon.md)
