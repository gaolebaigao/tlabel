# Migration Guide: v0.16 → v0.17

## ⚠️ Breaking Change

**v0.17.0 彻底移除了旧版 `tlabel_v2` (22维) 数据格式兼容。** 所有数据路径现在只走 **Schema V2 (14维结构化)**。

这意味着：
- 旧的 `TLabelFrame.tlabel_v2` 字典属性已删除
- 旧版生成的数据文件无法直接加载
- 所有适配器输出统一为 `TLabelSchemaV2` 对象

## 为什么这么做？

v0.16 及之前的 22 维架构存在根本问题：

1. **数据质量不可控**：不是所有传感器都能提供全部 22 维，大量字段填 0/None，下游无法区分"真实为 0"和"传感器不支持"
2. **同名字段语义不一致**：不同适配器的同名维度可能含义不同
3. **下游模型引入噪声**：模型无法判断数据质量，训练时混入大量无效字段

v0.17 通过 **14 维语义 Schema + Compliance Level (L1-L4)** 解决这些问题：
- 每个字段有明确的物理/语义定义
- Required/Optional 清晰标注
- 适配器如实声明能力等级，不再"假装完整"

## 具体变化

### ❌ 移除的 API

| 移除项 | 替代方案 |
|--------|----------|
| `TLabelFrame.tlabel_v2` | `TLabelFrame.schema_v2` |
| `TLabelFrame._original_tlabel` | 不再需要 |
| `predict/_compat.py` 兼容层 | 不需要 |
| `_detect_schema_version()` | 不需要 |
| `_detect_use_schema_v2()` | 不需要 |
| `quality/scorer.py` 中的 `LEGACY_V2_DIMS` | 使用 14 维 Schema |
| `augment/transforms.py` 中的 `LEGACY_V2_FEATURE_NAMES` | 使用 V2 `FEATURE_NAMES` |
| `export/writer.py` 中的 legacy 22 列 CSV 导出 | 只有 V2 展开列 (20列) |

### ✅ 新增的 API

| 新增项 | 说明 |
|--------|------|
| `TLabelFrame.schema_v2` | 必填，类型 `TLabelSchemaV2` |
| `TLabelSchemaV2` | 14 维 dataclass，含 Compliance Level |
| `TLabelSchemaV2.compliance_level` | 枚举 L1/L2/L3/L4 |
| `TLabelSchemaV2.force_magnitude` | 标量力 (N)，L2+ 约定必填 |
| `DataAdapterBase.extract_schema()` | 将原始数据转换为 `TLabelSchemaV2` |
| `DataAdapterBase.default_compliance_level` | 适配器声明能力等级 |
| `SensorAdapterBase.extract_schema()` | 实时传感器的 Schema V2 提取 |

### 🔄 行为变化

| 模块 | 变化 |
|------|------|
| `TLabelFrame.__init__()` | `schema_v2` 参数改为必填，传 None 抛 ValueError |
| `TLabelFrame.from_dict()` | 只支持 Schema V2 格式 |
| `TLabelFrame.to_dict()` | 只输出 Schema V2 格式 |
| `export/writer.py` | CSV 导出 20 列 (V2 展开)，HDF5 只写 V2 路径 |
| `predict/engine.py` | 预标注引擎完全重写，只读 Schema V2 字段 |
| `predict/force_estimator.py` | 力推断结果写入 `schema_v2.force_magnitude` |
| `predict/ml_engine.py` | 特征字段缩减为 5 个 V2 核心字段 |
| `quality/scorer.py` | 评分规则基于 14 维 Schema + Compliance Level |
| 所有 10 个适配器 | 统一改为 `TLabelFrame(schema_v2=TLabelSchemaV2.from_tlabel_v1(...))` |

## 迁移代码示例

### 1. 构造 TLabelFrame

**旧代码 (v0.16):**
```python
frame = TLabelFrame(
    frame_idx=0,
    timestamp_s=0.0,
    tlabel_v2={"contact": 1.0, "force_x": 0.5, ...}  # 22维字典
)
```

**新代码 (v0.17):**
```python
from tlabel.core.schema import TLabelSchemaV2

sv2 = TLabelSchemaV2(
    contact=True,
    contact_centroid=[32.5, 48.2],
    force_magnitude=1.5,
    compliance_level="L2",
)
frame = TLabelFrame(
    frame_idx=0,
    timestamp_s=0.0,
    schema_v2=sv2,  # 必填
)
```

### 2. 读取标注字段

**旧代码:**
```python
force_x = frame.tlabel_v2.get("force_x", 0.0)
contact = frame.tlabel_v2.get("contact", 0.0)
```

**新代码:**
```python
force_mag = frame.schema_v2.force_magnitude or 0.0
contact = 1.0 if frame.schema_v2.contact else 0.0
# 或使用便捷属性
contact = frame.contact
force_mag = frame.force_magnitude
```

### 3. 适配器开发

**旧代码:**
```python
class MyAdapter(BaseAdapter):
    def load(self, path):
        frames = []
        for raw in data:
            frame = TLabelFrame(tlabel_v2={"contact": 1.0, ...})
            frames.append(frame)
        return TLabelData(frames=frames)
```

**新代码:**
```python
from tlabel.adapters.base import DataAdapterBase
from tlabel.core.schema import TLabelSchemaV2

class MyAdapter(DataAdapterBase):
    default_compliance_level = "L2"
    
    def extract_schema(self, raw_frame_data) -> TLabelSchemaV2:
        return TLabelSchemaV2(
            contact=True,
            contact_centroid=[raw_frame_data["cx"], raw_frame_data["cy"]],
            force_magnitude=raw_frame_data["force"],
            compliance_level=self.default_compliance_level,
        )
    
    def load(self, path, **kwargs):
        frames = []
        for raw in data:
            sv2 = self.extract_schema(raw)
            frame = TLabelFrame(schema_v2=sv2, ...)
            frames.append(frame)
        return TLabelData(frames=frames, sensor_info=self.get_sensor_info())
```

### 4. 导出 CSV

**旧代码 (22列):**
```python
# 输出包含 force_x, force_y, force_z, deformation_1..5 等 22 列
tlabel.export(data, "output.csv")
```

**新代码 (20列 — V2 展开):**
```python
# 输出包含 contact, contact_centroid_x, contact_centroid_y, force_magnitude,
# force_vector_x, force_vector_y, force_vector_z, ... 等 20 列
tlabel.export(data, "output.csv")
```

## Compliance Level 速查

| Level | 名称 | 必填字段 | 典型传感器 |
|-------|------|----------|-----------|
| L1 | Basic | contact, contact_centroid, slip_event, confidence | TacQuad (仅图像) |
| L2 | Force-Aware | L1 + force_magnitude | PaXini, YCB-Slide, VTouch |
| L3 | Full-Vector | L2 + force_vector [Fx,Fy,Fz] | ToucHD, UniVTAC, GelSight(标定后) |
| L4 | Rich-Semantic | L3 + 所有 Optional 字段 | 理想化全传感器 |

## 需要帮助？

- GitHub Issues: https://github.com/liesliy/tlabel/issues
- 设计文档: https://github.com/liesliy/tlabel/blob/main/docs/TLabel_Design_Document.md
