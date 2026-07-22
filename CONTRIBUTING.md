# Contributing to TLabel

感谢你对 TLabel 项目的关注！TLabel 是触觉数据的统一标准中间件，我们欢迎社区贡献来扩展传感器覆盖范围。

## 贡献类型

### 1. 🟢 数据适配器（Data Adapter）— 零硬件门槛，推荐新手入门

将公开的触觉数据集格式转换为 TLabel v2 标准格式。你只需要：
- 目标数据集的样例文件（≤10MB）
- 了解数据集的格式结构

### 2. 🔵 传感器适配器（Sensor Adapter）— 需要硬件

通过厂商 SDK 实时读取传感器数据。你需要：
- 传感器硬件设备
- 厂商提供的 SDK/API 文档

### 3. 🟡 导出格式（Exporter）

新增下游训练框架的导出支持（如 Isaac Sim、Mujoco 等）。

### 4. 🐛 Bug 修复 / 文档改进 / 测试补充

随时欢迎！

---

## 快速开始（5 分钟创建数据适配器）

### Step 1: Fork 模板

```bash
# 从模板创建你的适配器项目
git clone https://github.com/liesliy/tlabel-adapter-template.git tlabel-adapter-<sensor_name>
cd tlabel-adapter-<sensor_name>
```

或直接复制本仓库的模板目录：

```bash
cp -r contrib/adapter-template/ tlabel-adapter-<sensor_name>/
```

### Step 2: 实现适配器

编辑 `adapter/my_sensor.py`，重命名为你传感器的名称，实现以下接口：

```python
from tlabel.adapters.base import DataAdapterBase
from tlabel.core.types import TLabelData, TLabelFrame

class MySensorAdapter(DataAdapterBase):
    @property
    def name(self) -> str:
        return "my_sensor"  # 唯一标识符，小写+下划线

    @property
    def supported_extensions(self) -> list:
        return [".csv", ".dat"]  # 你的数据文件扩展名

    def load(self, file_path, trajectory_id=None, **kwargs) -> TLabelData:
        """将原始数据转换为 TLabelData"""
        # 1. 读取原始数据文件
        # 2. 映射到 22 维 tlabel_v2 特征
        # 3. 组装 TLabelFrame 列表
        # 4. 返回 TLabelData
        ...

    def get_capabilities(self) -> dict:
        """声明你的传感器支持哪些维度"""
        return {
            "contact": True,
            "deformation_magnitude": True,
            "force_magnitude": False,
            # ... 22 个维度，支持为 True，不支持为 False
        }

    def get_sensor_info(self) -> dict:
        """传感器元信息"""
        return {
            "type": "your_sensor_type",
            "manufacturer": "your_company",
            "model": "your_model",
        }
```

### Step 3: 本地验证

```bash
# 安装 tlabel
pip install tlabel

# 运行测试
pip install pytest
pytest tests/ -v

# 验证 Schema 兼容性
python -c "
from tlabel.core.schema import validate_tlabel_v2
from adapter.my_sensor import MySensorAdapter
adapter = MySensorAdapter()
data = adapter.load('data/sample/')
result = validate_tlabel_v2(data.to_dict())
assert result.valid, f'Schema validation failed: {result.errors}'
print('✅ Schema validation passed')
"
```

### Step 4: 提交 PR

1. 将你的适配器推送到你的 GitHub fork
2. 向 `liesliy/tlabel` 提交 Pull Request
3. CI 会自动运行测试和 Schema 校验
4. 维护者会在 3 个工作日内 review

---

## 22 维 tlabel_v2 特征空间

你的适配器需要尽可能将原始数据映射到以下 22 个维度。不支持的维度填 `0.0` 或在 `get_capabilities()` 中标记为 `False`。

| 维度 | 类型 | 说明 |
|------|------|------|
| `contact` | bool→float | 接触状态 (0.0/1.0) |
| `deformation_magnitude` | float | 形变幅度 (归一化 0-1) |
| `force_magnitude` | float | 力大小 (deprecated, 用 normal_field) |
| `force_peak` | float | 峰值力 |
| `force_direction` | float | 力方向 (弧度) |
| `slip_entropy` | float | 滑移熵 |
| `slip_event` | bool→float | 滑移事件 (0.0/1.0) |
| `texture_energy` | float | 纹理能量 |
| `edge_density` | float | 边缘密度 |
| `contact_area` | float | 接触面积 (归一化 0-1) |
| `centroid_x` | float | 接触中心 X (归一化 0-1) |
| `normal_field_magnitude` | float | 法向力场幅度 |
| `normal_field_variance` | float | 法向力场方差 |
| `shear_field_magnitude` | float | 剪切力场幅度 |
| `shear_field_direction` | float | 剪切力场方向 |
| `delta_force_normal` | float | 法向力变化量 |
| `delta_force_shear` | float | 剪切力变化量 |
| `friction_cone_ratio` | float | 摩擦锥比率 |
| `optical_flow_magnitude` | float | 光流幅度 |
| `optical_flow_direction` | float | 光流方向 |
| `temporal_deformation_rate` | float | 时间形变率 |
| `contact_transition` | float | 接触状态转换 |

---

## 提交要求

- [ ] CI 自动化测试通过（GitHub Actions）
- [ ] 包含样例数据（≤10MB）或数据下载脚本
- [ ] 包含 README.md 说明传感器/数据集信息
- [ ] 包含至少 1 个 Jupyter Notebook 使用示例
- [ ] Schema 校验通过（tlabel_v2 格式兼容性）
- [ ] `get_capabilities()` 准确反映传感器实际能力
- [ ] 代码风格与项目一致（PEP 8）

## 审核标准

1. **代码可运行** — CI 通过是硬性门槛
2. **输出合规** — 符合 tlabel_v2 Schema（22 维特征空间）
3. **文档清晰** — README + Notebook 示例让新用户 5 分钟上手
4. **无功能重复** — 不与已有适配器功能重复

## 不接收的情况

- ❌ 纯 placeholder（骨架代码无实际实现）
- ❌ 无法提供样例数据且无下载脚本
- ❌ 绑定特定商业 SDK 但无免费层可用

## 代码规范

- 遵循 PEP 8
- 使用 type hints
- Commit message 遵循 [Conventional Commits](https://www.conventionalcommits.org/)
  - 适配器新增: `adapter: add XXX sensor support`
  - Bug 修复: `fix: correct XXX in YYY adapter`
  - 文档: `docs: update XXX`

## 需要帮助？

- 在 GitHub Issues 中提问
- 参考已有适配器的实现：[tlabel/adapters/](https://github.com/liesliy/tlabel/tree/main/tlabel/adapters)
- 查看开发者指南: [internal-docs/DEVELOPER_GUIDE.md](https://github.com/liesliy/tlabel/blob/main/internal-docs/DEVELOPER_GUIDE.md)
