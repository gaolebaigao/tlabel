> ⚠️ 内部文件，不进git仓库。含论文策略和BD话术。

**Version:** v2.1 | **Last Updated:** 2026-07-24

---

## 1. 当前适配器 Compliance Level 映射

| 适配器 | Level | 依据 |
|--------|-------|------|
| Paxini Gen3 (实时) | L2 | 只有 total_force_n（法向标量力） |
| Paxini Dataset | L2 | 同上 |
| YCB-Slide | L2 | deformation_mag 近似法向力 |
| DM-TAC (实时) | L2-L3 | 可通过 deformation+shear 合成 3D 力，但需标定 |
| GelSight (数据集) | L2-L3 | 视触觉，可从图像提取力信息 |
| Daimon Dataset | L2-L3 | deformation/shear/depth 三路视频 |
| ToucHD | L3 | 真实 3D 力标签 (Fx, Fy, Fz) |
| UnivTac | L2-L3 | 有 force_magnitude + shear |
| TacQuad | L1-L2 | Tac3D 有近似力，其他只有图像 |
| VTouch | L2 | 有力信息 |

> **注意**：L2-L3 表示该适配器可根据标定精度选择标注 L2 或 L3。未标定时默认 L2。

---

## 2. 论文叙事指南

### 2.1 核心贡献（必须按此框架表述）

1. **格式标准**（Section III）
   - 提出14维语义空间的触觉数据交换格式，含 Compliance Level（L1-L4）分层机制
   - 物理基础：Lederman & Klatzky 触觉探索分类
   - 数据验证：跨 M 个数据集、N 帧标注覆盖率达 95%+

2. **跨传感器互通**（Section IV）
   - 不同传感器（GelSight, PaXini, ...）填充同一套 Schema
   - 验证：Schema-level 互操作性，optional 字段的合法缺失

3. **下游任务验证**（Section V）
   - 基于 TLabel 标注派生任务特征
   - Grasp stability / texture classification / slip detection
   - 消融实验证明各语义维度组的贡献

### 2.2 禁止出现的表述

| ❌ 禁止 | ✅ 替代 |
|---|---|
| "TLabel defines 18/22/26 semantic features" | "TLabel defines a 14-dimensional semantic schema with Compliance Level L1-L4" |
| "TLabel features include color statistics" | "For downstream evaluation, we derive task-specific features from TLabel annotations" |
| "PaXini has 7 zero dimensions" | "PaXini is L2 compliant; it does not populate optional fields such as texture_class and slip_velocity, which is valid per the schema specification" |
| "Our 18-dimensional feature vector" | "Our task-specific 18-dimensional feature vector derived from TLabel annotations" |

### 2.3 维度设计理由段落（Section III-B 建议文本）

> **Dimension Taxonomy Design.** The 14 semantic dimensions are grounded in the physical interaction taxonomy for robotic manipulation. Drawing on the haptic exploration framework (Lederman & Klatzky, 1987) and tactile sensing surveys (Bicchi & Robb, 2000; Yuan et al., 2023), we organize the dimensions into four physical categories:
>
> - **Spatial perception**: contact state, contact centroid, contact region, and object deformation characterize the geometry of interaction.
> - **Mechanical perception**: force magnitude, force vector, and torque vector provide a complete wrench description of the contact.
> - **Surface perception**: texture class and temperature capture material attributes accessible through touch.
> - **Dynamic perception**: slip event and slip velocity characterize incipient and gross slip dynamics.
>
> Two meta-dimensions—manipulation phase, annotation confidence, and compliance level—provide task context, provenance tracking, and data capability transparency, respectively. The Compliance Level mechanism (L1–L4) ensures that sensors with different physical capabilities can all participate in the standard at their appropriate level.
>
> To validate coverage, we annotated [N] frames across [M] public datasets using the proposed schema. Table X shows that...

---

## 3. 社区沟通话术

### 3.1 对外介绍（BD / README / 社交媒体）

> TLabel is a **sensor-agnostic data exchange format** for robotic tactile sensing. It defines a 14-dimensional semantic schema with a Compliance Level mechanism (L1–L4) that any tactile sensor can map to, enabling cross-platform data sharing, benchmarking, and reuse. TLabel does not prescribe how to extract features—it provides a common language for describing what happened during a tactile interaction.

### 3.2 关键区分（必须反复强调）

- "TLabel 是格式标准" ✅
- "TLabel 是特征提取方法" ❌
- "TLabel 定义14个语义维度 + L1-L4 合规等级" ✅
- "TLabel 定义18维特征向量" ❌
- "TLabel 的 adapter 输出18维 flat vector" ❌

### 3.3 常见误解及回应

| 问题 | 回应 |
|------|------|
| "TLabel 和 ROS msg 有什么区别？" | ROS msg 定义通信消息格式，TLabel 定义触觉语义标注。两者互补：TLabel 可以用 ROS msg 传输，但 TLabel 的语义定义是传感器无关的。 |
| "为什么不是18维/22维？" | 14维是 Schema 层（语义描述+合规等级），18维是下游任务派生特征层。前者是标准，后者是应用。 |
| "我的传感器不支持温度怎么办？" | temperature 是 optional 字段，填 null 即可。Schema 设计上就考虑了不同传感器的能力差异。 |
| "TLabel 能用于深度学习吗？" | TLabel 提供结构化标注，你可以从中派生任何特征用于模型训练。它不限制下游方法。 |
