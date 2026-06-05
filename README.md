# TouchLabel AI — Tactile Data Annotation Toolkit

> 触觉数据标注工具包 · pip install 一行搞定

## 安装

```bash
# 基础安装
pip install tlabel

# 带GelSight/DIGIT支持
pip install tlabel[gelsight]

# 带帕西尼支持
pip install tlabel[paxini]

# 带戴盟支持
pip install tlabel[daimon]

# 全部传感器
pip install tlabel[all]
```

## 5分钟上手

```python
import tlabel

# 加载数据 — 自动识别格式
data = tlabel.load("gelsight_force.pkl")     # GelSight/DIGIT
data = tlabel.load("paxini_episode.h5")      # 帕西尼
data = tlabel.load("daimon_data/")           # 戴盟（目录或.parquet）

# 弹出彩色标注面板（Jupyter）
data.review()

# 英文界面
data.review(lang="en")

# 导出
data.export("output.json")    # TLabel Format v2 JSON
data.export("output.csv")     # CSV平面表
```

## 支持的传感器

| 传感器 | 格式 | 状态 |
|--------|------|------|
| GelSight Mini | .pkl | ✅ 第一期 |
| DIGIT | .pkl | ✅ 第一期 |
| PaXini PXCap | .h5/.hdf5 | ✅ 第一期 |
| Daimon DM-TacClaw | .parquet / 目录 | ✅ 支持 |

## 交互面板功能

- 🎨 **彩色时间轴**：绿=接触、红=滑移、灰=无接触
- 🕸 **18维雷达图**：TLabel Format v2全部维度可视化
- ✏️ **批量修正**：选中帧区间，一键修改接触/滑移/力度
- 🔗 **联动规则**：接触=0时自动清除力度和滑移
- 🌐 **中英文切换**：右上角一键切换
- 📤 **导出**：JSON / CSV

## TLabel Format v2 (18维)

```
# v1 (11维)
contact · deformation_magnitude · force_magnitude · force_peak
force_direction · slip_entropy · slip_event · texture_energy
edge_density · contact_area · centroid_x

# v2新增 (7维)
normal_field_magnitude · normal_field_variance
shear_field_magnitude · shear_field_direction
delta_force_normal · delta_force_shear · friction_cone_ratio
```

## License

MIT © 牛宿科技
