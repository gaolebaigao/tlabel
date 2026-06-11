# Daimon DM-TacClaw 传感器标注教程

本教程演示如何为 Daimon DM-TacClaw 多模态机器人（含触觉视觉）的数据添加标注。

## 前置准备

```bash
pip install tlabel[daimon]
```

这会安装 `pyarrow`（读取 Parquet）和 `opencv-python`（处理触觉视频）。

**额外要求：** 系统需要安装 `ffmpeg`，用于解码 FFV1 编码的触觉视频。

```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Windows: 从 https://ffmpeg.org/download.html 下载并添加到 PATH
```

## 步骤 1: 准备数据

Daimon 数据采用 LeRobot 风格的目录结构：

```
daimon_episode/
├── meta/
│   └── info.json          # Episode 元数据
├── data/
│   ├── chunk-0000.parquet # 观测数据 (114维 state 向量)
│   └── chunk-0001.parquet # ...
└── videos/
    ├── tactile_left.mov   # FFV1 编码的左手指触觉视频
    └── tactile_right.mov  # FFV1 编码的右手指触觉视频
```

**关键说明：**
- `observation.state` 是 114 维向量，包含机器人关节角度、末端位姿、IMU 等
- 触觉视频是 16-bit grayscale (gray16le) 或 RGB (gbrp16le)，FFV1 无损编码
- 如果 `videos/` 目录不存在或视频文件缺失，适配器会优雅降级（只输出非视觉维度）

## 步骤 2: 加载数据

```python
import tlabel

# 加载目录（自动识别为 Daimon 格式）
data = tlabel.load("path/to/daimon_episode/")

print(f"加载了 {data.num_frames} 帧")
print(f"传感器类型: {data.sensor_type}")
print(f"视频可用: {data[0].sensor_specific.get('video_available', False)}")
```

**发生了什么：**
1. 适配器读取 `meta/info.json` 获取 episode 元数据
2. 读取 `data/chunk-*.parquet` 文件，提取 114 维 state 向量
3. 解析 state 向量中的触觉相关维度（索引 68-107，共 40 维触觉状态）
4. 如果有视频文件，用 ffmpeg 解码 FFV1 视频，逐帧提取触觉特征：
   - 变形幅度（deformation_magnitude）
   - 接触面积（contact_area）
   - 纹理能量（texture_energy）
   - 边缘密度（edge_density）
   - 法向场/剪切场
5. 融合 state 向量和视频特征，输出 22 维 TLabel 特征
6. 推断操作阶段

## 步骤 3: 查看和修正标注

```python
data.review()
```

**Daimon 特有的注意事项：**
- Daimon 是最复杂的传感器，融合了机器人状态和触觉视觉
- 如果视频不可用，部分维度会用占位值（9930.0）或 0 填充
- `sensor_specific` 中包含丰富的额外信息：
  - `gripper_left` / `gripper_right`: 夹爪开合度
  - `right_acc` / `right_gyro`: IMU 数据
  - `robot_type`: 机器人类型（如 "aloha"）
  - `video_available`: 视频是否成功解码

**常见问题及修正方法：**

| 问题 | 表现 | 修正方法 |
|------|------|----------|
| 视频解码失败 | video_available=False | 检查 ffmpeg 是否安装，视频文件是否存在 |
| 占位值过多 | 很多维度是 9930.0 | 这是 Daimon 数据集的禁用维度标记，正常现象 |
| 帧数不匹配 | Parquet 和视频帧数不一致 | 适配器会以较少的一方为准，检查数据完整性 |

## 步骤 4: 导出标注

```python
data.export("daimon_annotated.json")
data.export("daimon_annotated.csv")
```

## 进阶技巧

### 检查视频解码状态

```python
frame = data[0]
if not frame.sensor_specific.get('video_available', False):
    print("警告: 视频不可用，部分维度可能缺失")
    print(f"视频类型: {frame.sensor_specific.get('video_type', 'N/A')}")
```

### 提取机器人状态

```python
# Daimon 的 sensor_specific 包含丰富的机器人状态
for i in range(min(10, data.num_frames)):
    frame = data[i]
    ss = frame.sensor_specific
    print(f"帧 {i}: gripper_left={ss.get('gripper_left')}, "
          f"gripper_right={ss.get('gripper_right')}")
```

### 批量处理多个 episode

```python
from pathlib import Path

episodes_dir = Path("path/to/daimon_dataset/")
all_data = []

for episode_path in episodes_dir.iterdir():
    if episode_path.is_dir():
        try:
            data = tlabel.load(str(episode_path))
            all_data.append(data)
            print(f"加载 {episode_path.name}: {data.num_frames} 帧")
        except Exception as e:
            print(f"加载失败 {episode_path.name}: {e}")

print(f"成功加载 {len(all_data)} 个 episode")
```

## 常见问题

### Q: ffmpeg 找不到怎么办？

A: 确保 ffmpeg 在系统 PATH 中：
```bash
# 测试 ffmpeg 是否可用
ffmpeg -version

# 如果找不到，手动指定路径（Windows）
# 将 ffmpeg.exe 所在目录添加到系统环境变量 PATH
```

### Q: 视频解码很慢怎么办？

A: FFV1 是无损编码，解码比较耗时。优化建议：
1. 确保使用较新版本的 ffmpeg（2020+）
2. 如果是 SSD，解码速度会快很多
3. 未来版本可能支持多线程解码

### Q: 9930.0 是什么？

A: 9930.0 是 Daimon 数据集中的占位值，表示该维度在此传感器上不可用或被禁用。适配器会自动将这些值转换为 0 或 None。

### Q: 我的 Daimon 数据不是 LeRobot 格式怎么办？

A: 如果你的数据是单独的 Parquet 文件或视频文件，可以：
1. 手动构建 LeRobot 目录结构（创建 meta/info.json，移动 parquet 和 video）
2. 或者写一个转换脚本，将数据转换成标准格式
3. 联系我们添加对其他格式的支持

---

[返回 README](../README.md) | [GelSight 教程](tutorial-gelsight.md) | [PaXini 教程](tutorial-paxini.md)
