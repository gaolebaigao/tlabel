# tlabel-adapter-<SENSOR_NAME>

TLabel 适配器 — <传感器/数据集名称>

## 概述

本适配器将 <传感器/数据集名称> 的原始数据转换为 [TLabel](https://github.com/liesliy/tlabel) 统一的 22 维 tlabel_v2 格式。

- **传感器类型**: <视触觉/阵列式/霍尔效应/...>
- **制造商**: <厂商名称>
- **数据来源**: <公开数据集 URL 或 SDK 文档链接>
- **支持的维度**: <列出支持的维度数量>/22

## 安装

```bash
pip install tlabel
# 如有额外依赖
pip install <extra-dependency>
```

## 快速开始

```python
from adapter.my_sensor import MySensorAdapter

adapter = MySensorAdapter()
data = adapter.load("path/to/data/")

# 查看基本信息
print(f"帧数: {data.num_frames}")
print(f"时长: {data.duration:.2f}s")

# 导出为不同格式
from tlabel.export.writer import Exporter
exporter = Exporter()
exporter.to_json(data, "output.json")
exporter.to_csv(data, "output.csv")
```

## 支持的 tlabel_v2 维度

| 维度 | 支持 |
|------|------|
| contact | ✅ |
| deformation_magnitude | ✅ |
| contact_area | ✅ |
| centroid_x | ✅ |
| ... | ... |

运行 `python -c "from adapter.my_sensor import MySensorAdapter; print(MySensorAdapter().get_capabilities())"` 查看完整列表。

## 样例数据

`data/sample/` 目录包含少量样例数据，可直接运行测试：

```bash
pytest tests/ -v
```

## 许可证

MIT
