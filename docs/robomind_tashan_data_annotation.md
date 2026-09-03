# RoboMIND V2.0 Tashan TS-F-A 触觉数据标注说明

> 2026-09-03 更新：以下 HDF5 结构已通过实际数据验证（data/ 1294帧 + data1/ 2066帧）

> 基于 RoboMIND 2.0 论文 + 社区转换工具 + 实际数据验证

## 数据来源

- **数据集**：RoboMIND V2.0（北京人形机器人创新中心 + 北京大学）
- **平台**：AgileX Cobot Magic V2.0 移动双臂机器人
- **传感器**：Tashan TS-F-A（他山科技）3D Force 指尖力传感器
- **规模**：12,000 条触觉增强轨迹（约占总量 310K 的 3.9%）
- **论文**：[RoboMIND 2.0 (arXiv:2512.24653)](https://arxiv.org/abs/2512.24653)

## 传感器配置

AgileX 的平行爪夹爪每个手指上安装一个 Tashan TS-F-A 触觉传感器，每个传感器包含 2 个独立传感模块，每个模块实时采集 6 维数据：

| 维度 | 名称 | 含义 | 单位 |
|------|------|------|------|
| dim0 | normal_force | 法向力 | N |
| dim1 | tangential_force | 切向力幅值 | N |
| dim2 | tangential_direction | 切向力方向 | rad |
| dim3 | tangential_fx | 切向力 x 分量 | N |
| dim4 | tangential_fy | 切向力 y 分量 | N |
| dim5 | contact_indicator | 接触指示 | - |

> **65535.0 (0xFFFF)** 为 uint16 溢出无效值标记

## HDF5 数据结构

```
trajectory.hdf5
└── tactile_observations/
    ├── tactile_left_align/
    │   ├── data/       (T, 2, 6) float32
    │   ├── is_intervene/ (T,) bool
    │   └── timestamp/  (T,) int64
    └── tactile_right_align/
        ├── data/       (T, 2, 6) float32
        ├── is_intervene/ (T,) bool
        └── timestamp/  (T,) int64
```

## 与 TLabel Schema V2 的映射

| TLabel 字段 | 映射来源 | 合规等级 |
|------------|----------|----------|
| contact | any(normal_force > 0.01) | L1 |
| force_magnitude | normal_force (dim0) | L2 |
| force_vector | [tangential_fx, tangential_fy, normal_force] | L3 |
| slip_event | 切向力变化率检测 | L3 |

## 适配器信息

- **适配器名**: tashan_ts_f_a
- **类名**: TashanTsFAAdapter
- **Compliance Level**: L3
- **安装**: pip install tlabel[tashan]（需要 h5py）

```python
import tlabel
data = tlabel.load("trajectory.hdf5", format="tashan_ts_f_a")
```

## 参考

- [RoboMIND 2.0 论文](https://arxiv.org/abs/2512.24653)
- [Tashan 他山科技](https://tashantec.com)
- [TLabel 项目](https://github.com/liesliy/tlabel)
