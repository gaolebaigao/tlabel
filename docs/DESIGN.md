**Version:** v2.1 | **Last Updated:** 2026-07-24

---

## 1. 设计哲学

### 1.1 TLabel 是什么，不是什么

| ✅ TLabel 是 | ❌ TLabel 不是 |
|---|---|
| 触觉数据的**交换格式标准** | 特征提取算法或方法 |
| 传感器无关的**语义描述规范** | 某个传感器的专有数据格式 |
| 跨平台互操作的**通用中间层** | 端到端的感知管线 |
| 类比：COCO format、USB协议、ROS msg | 类比：YOLO、ResNet、特定SDK |

**一句话定位**：TLabel 之于触觉数据，正如 COCO format 之于计算机视觉——定义"数据长什么样"，不管"你怎么算"。

### 1.2 核心设计原则

1. **格式标准 ≠ 参考实现**
   - Schema 定义语义字段的类型、单位、取值范围
   - Adapter 是从传感器原始数据到 Schema 的映射工具
   - 两者独立演进，Schema 极度稳定，Adapter 可以频繁迭代

2. **Sensor-agnostic by design**
   - 任何传感器都可以填充同一套 Schema
   - 某些字段对某些传感器不可用 → 标记为 `null`，不是缺陷，是设计预期
   - 类比：COCO 的 keypoints 对侧面人体标注 `v=0` 完全合法

3. **可扩展但不膨胀**
   - 核心字段（required）保持精简
   - 扩展字段（optional）按需添加
   - 新增字段 = Schema 版本升级，需向后兼容

4. **维度选择靠数据说话**
   - 不在 Schema 文档里做哲学辩论
   - 在论文里用覆盖率、消融实验、任务性能来论证

---

## 2. 三层架构

```
┌─────────────────────────────────────────────────────────┐
│  Layer 3: 特征派生（Derived Features）                    │
│  ─────────────────────────────────────────                │
│  • 下游研究者根据任务自定义特征集                            │
│  • 每个任务可以有完全不同的特征维度                          │
│  • 与 TLabel 标准无关                                      │
│  • 例：grasp stability → 18维特征；texture → 频谱特征      │
│  • 论文消融实验属于此层                                    │
├─────────────────────────────────────────────────────────┤
│  Layer 2: 参考实现（Reference Implementation）             │
│  ─────────────────────────────────────────                │
│  • tlabel.adapters.* — 各传感器的数据映射                   │
│  • 从 raw sensor data → Layer 1 的语义字段                 │
│  • 不同传感器有不同的实现，输出格式统一                      │
│  • 可选字段对不支持的传感器填 null                           │
│  • 类比：cocoapi, pycocotools                             │
├─────────────────────────────────────────────────────────┤
│  Layer 1: Schema（标准核心）                               │
│  ─────────────────────────────────────────                │
│  • tlabel-schema.json — 12个语义维度定义                   │
│  • 每个字段的类型、单位、取值范围、required/optional         │
│  • 极度稳定，变更需版本升级                                 │
│  • 这是 TLabel 标准本身                                    │
│  • 类比：COCO JSON format, USB spec                       │
└─────────────────────────────────────────────────────────┘
```

### 层间关系

```
传感器原始数据 ──[Layer 2: Adapter]──→ Schema 语义标注（Layer 1）
                                              │
                                    [Layer 3: 特征派生]
                                              │
                                              ▼
                                     任务特定特征向量
                                     (grasp/texture/slip...)
```

- **Layer 1 → Layer 2**：Adapter 读取 Schema 定义，知道需要输出哪些字段
- **Layer 1 → Layer 3**：下游任务读取 Schema 标注，派生自己的特征
- **Layer 2 ↛ Layer 3**：Adapter 输出不直接给下游用，中间经过 Layer 1 解耦

---

## 3. Schema 定义（Layer 1）— 14 维语义空间

### 3.1 维度总览

| # | 字段名 | 类型 | 必选 | 物理含义 | 单位 |
|---|--------|------|------|----------|------|
| 1 | `contact` | bool | ✅ | 接触状态 | — |
| 2 | `contact_centroid` | [float, float] | ✅ (当contact=true) | 接触中心坐标 | 传感器像素坐标 or mm |
| 3 | `contact_region` | enum | ❌ | 粗粒度接触区域 | — |
| 4 | `force_magnitude` | float | ✅ (L2+) | 法向接触力标量 | N |
| 5 | `force_vector` | [float×3] | ❌ | 三维接触力 (Fx, Fy, Fz) | N |
| 6 | `torque_vector` | [float×3] | ❌ | 三维力矩 (Mx, My, Mz) | N·m |
| 7 | `slip_event` | bool | ✅ | 滑动检测 | — |
| 8 | `slip_velocity` | [float×2] | ❌ (当slip_event=true) | 滑动速度向量 | mm/s |
| 9 | `manipulation_phase` | enum | ❌ | 操作阶段 | — |
| 10 | `texture_class` | enum | ❌ | 纹理类别 | — |
| 11 | `object_deformation` | float | ❌ | 物体形变量 | mm or ratio |
| 12 | `temperature` | float | ❌ | 接触面温度 | °C |
| 13 | `confidence` | float | ✅ | 标注置信度 | 0.0 ~ 1.0 |
| 14 | `compliance_level` | enum | ✅ | 合规等级 (L1/L2/L3/L4) | — |

> **总计 14 个字段**：4 个无条件 Required（contact, slip_event, confidence, compliance_level）+ 1 个条件 Required（contact_centroid, 当 contact=true）+ 9 个 Optional（其中 force_magnitude 为 L2+ 合规的约定必填项）。

### 3.2 设计决策记录

#### 为什么是12个维度？

**物理基础**（Lederman & Klatzky 1987; Bicchi & Robb 2000）：

人类触觉感知有四大探索维度：
1. **空间感知**（Spatial）→ contact, contact_centroid, contact_region, object_deformation
2. **力学感知**（Mechanical）→ force_vector, torque_vector
3. **表面感知**（Surface）→ texture_class, temperature
4. **动态感知**（Kinetic）→ slip_event, slip_velocity

加上元信息层：
- `manipulation_phase`：任务上下文（同一组触觉信号在不同阶段含义不同）
- `confidence`：数据质量元信息（标注系统的可追溯性）

#### 关键设计决策

| 决策 | 选择 | 替代方案 | 理由 |
|------|------|----------|------|
| 力用向量还是标量？ | `force_magnitude` (L2+ 必填) + `force_vector` (L3+ Optional) | 只保留 `force_vector [Fx,Fy,Fz]` 为 Required | **物理现实约束**：Paxini Gen3 只有法向力通道，物理上无法测剪切力；YCB-Slide 的 force_direction 恒为 0.0。若 force_vector 为 Required，这些传感器无法合规。分层方案：L2 用标量力（几乎所有传感器都能填），L3 用 3D 向量（仅高端传感器） |
| 接触位置用枚举还是坐标？ | `contact_centroid [x,y]` (required) + `contact_region` (optional) | 只用 `contact_region` enum | 下游任务（grasp stability）需要精确坐标；枚举太粗无法支撑量化分析 |
| 滑动用方向还是速度？ | `slip_velocity [vx,vy]` | `slip_direction` unit vector | 速度包含方向和幅值信息，物理上更完整 |
| 纹理用字符串还是枚举？ | `texture_class` enum | `texture` string | 字符串无法跨数据集统一，枚举可以标准化（smooth/rough/granular/fibrous等） |
| whole_hand_coordination？ | 移出单帧 Schema | 保留在单帧 | 这是多帧/多指聚合属性，属于sequence-level annotation，不应污染单帧定义 |
| 新增 confidence？ | 必选 | 不需要 | 标注系统的可追溯性是数据标准的基本素养（参考 VIDS provenance tracking） |
| 新增 compliance_level？ | 必选 (L1/L2/L3/L4) | 不需要 | 让下游用户明确知道数据的信息密度和可信度边界，避免将 L1 数据误当 L3 使用 |

#### 向后兼容策略

- 从 v1.x（10维）升级到 v2.0（12维），再到 v2.1（14维）：
  - `contact_centroid`：新增 required，旧数据需补标或标 null
  - `force_vector`：从 Required 降为 Optional（L3+），由 `force_magnitude` + `force_direction` 合并；同时新增 `force_magnitude` 作为 L2+ 约定必填项
  - `slip_velocity`：替代 `slip_direction`，可自动转换（方向 → 单位速度向量）
  - `texture_class`：替代 `texture` string，需提供映射表
  - `torque_vector`、`temperature`：新增 optional，旧数据直接为 null
  - `confidence`：新增 required，旧数据默认 1.0
  - `whole_hand_coordination`：移至 optional metadata，不影响核心

### 3.3 Compliance Level（合规等级分层）

不同传感器和数据集的物理能力差异巨大。TLabel 通过 Compliance Level 分层，让所有传感器都能在统一框架下合规，同时让下游用户清楚每帧数据的信息密度。

| Level | 名称 | 必填字段 | 适用传感器/数据集 |
|-------|------|---------|------------------|
| **L1 Basic** | 基础触觉 | contact, contact_centroid, slip_event, confidence | 所有传感器（包括单点压阻、接近觉等最基础设备） |
| **L2 Force-Aware** | 力感知 | L1 + **force_magnitude** (标量法向力) | 能测法向接触力的（Paxini, YCB-Slide, DM-TAC, GelSight 等） |
| **L3 Full-Vector** | 完整力向量 | L2 + **force_vector** [Fx, Fy, Fz] | 能测 3D 接触力的（ToucHD, 标定后的 DM-TAC/GelSight） |
| **L4 Rich-Semantic** | 完整语义 | L3 + 所有 Optional 字段（torque, texture, temperature 等） | 高端多模态传感器（BioTac 等）或未来硬件 |

#### 设计原则

1. **累积式**：L3 必然满足 L2 和 L1 的所有要求
2. **物理现实优先**：Paxini Gen3 物理上无法测剪切力，强制标 L2 而非"不合规"
3. **下游可判断**：`compliance_level` 字段让模型/算法明确知道数据边界
4. **Adapter 自动标注**：每个 Adapter 根据自身传感器能力自动设置 compliance_level，用户无需手动指定

#### 与字段 Required/Optional 的关系

- Schema 层面：只有 4 个字段无条件 Required（contact, slip_event, confidence, compliance_level）
- 合规层面：L2+ 要求 force_magnitude 非 null；L3+ 要求 force_vector 非 null
- Validator 校验逻辑：先检查 Schema Required，再根据 compliance_level 检查条件必填

---

## 4. 参考实现（Layer 2）— 适配器设计原则

### 4.1 Adapter 的职责

```python
class SensorAdapterBase:
    """从特定传感器原始数据中提取 TLabel Schema 语义字段"""

    def extract(self, raw_data) -> dict:
        """
        返回符合 tlabel-schema.json 的字典。
        - Required 字段必须填充（或合理标注 null）
        - Optional 字段不支持时填 null，不填 0
        """
        raise NotImplementedError
```

### 4.2 关键原则

- **不支持的字段填 `null`，不填 `0`**
  - `0` 是有意义的数值（= 力为零）
  - `null` 表示"传感器不支持此字段"
  - 这是 PaXini 7维为0 的根本修复

- **每个 Adapter 自动标注 compliance_level**
  - Adapter 根据自身传感器物理能力自动设定 L1-L4
  - GelSight：L2-L3（视触觉可合成3D力，但需标定）
  - PaXini：L2（只有法向力标量）
  - BioTac：L4（有温度、振动频谱、3D力）
  - 它们输出同一个 Schema，只是 compliance_level 不同

- **Adapter 不输出 flat vector**
  - 输出是结构化字典，不是 18 维 numpy array
  - Flat vector 是 Layer 3 的事

---

## 5. 特征派生（Layer 3）— 下游任务示例

### 5.1 示例：Grasp Stability Prediction

```python
def derive_grasp_features(tlabel_annotation: dict) -> np.ndarray:
    """从 TLabel 标注派生 grasp stability 特征"""
    features = []

    # Geometry (from contact_centroid + contact_region)
    features.append(contact_area)
    features.append(centroid_x)
    features.append(centroid_y)
    features.append(contact_width)
    features.append(contact_height)

    # Color statistics (from original sensor image, NOT from TLabel)
    features.append(rgb_mean_r)
    features.append(rgb_mean_g)
    features.append(rgb_mean_b)
    features.append(rgb_std_r)
    features.append(rgb_std_g)
    features.append(rgb_std_b)

    # Force proxy (from force_vector)
    features.append(force_magnitude)      # = norm(force_vector)
    features.append(force_shear_x)        # = force_vector[0]
    features.append(force_shear_y)        # = force_vector[1]
    features.append(force_normal)         # = force_vector[2]

    # Shape descriptors (derived)
    features.append(asymmetry)
    features.append(eccentricity)
    features.append(edge_sharpness)

    return np.array(features)  # 18-dim, task-specific
```

### 5.2 关键区分

| 特征来源 | 属于哪层 | 是否标准化 |
|----------|---------|-----------|
| contact_centroid = [120, 85] | Layer 1 (Schema) | ✅ 标准化 |
| force_vector = [0.1, -0.3, 2.5] | Layer 1 (Schema) | ✅ 标准化 |
| "RGB mean = 128" | Layer 3 (下游派生) | ❌ 任务特定 |
| 18维 numpy array | Layer 3 (下游派生) | ❌ 任务特定 |
