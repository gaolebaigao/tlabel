# Changelog

All notable changes to TLabel will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.1] - 2025-01-XX

### Fixed
- **i18n补全**：热力图和统计页面中文适配
  - 雷达图维度标签（22维特征）使用i18n国际化
  - 统计摘要表格（describe）的行名和列名支持中英文切换
  - 新增 `dim.*` 和 `stats.*` i18n key
- **深色模式数字不可读**：统计页和质量页在暗色模式下数字颜色修复
  - `renderDescribe()` 和 `renderQuality()` 根据 `isDark` 变量选择颜色
  - 切换暗色模式后自动重新渲染统计数据
- **Episode语义标注保存反馈优化**
  - 反馈持续时间从2秒延长至4秒
  - 反馈信息更详细，显示"Episode标注已保存（将随导出数据一起输出）"
  - 保存按钮点击后短暂禁用，防止重复点击

### Changed
- **QUICKSTART.md** 全面更新，使用 v0.5.0+ API
  - 新增 `tlabel.demo()` 快速体验
  - 更新数据加载方式为 `tlabel.load()`
  - 新增 AI 预标注（PredictEngine）说明
  - 更新 VTouch 数据格式支持说明

## [0.5.0] - 2024-12-XX

### Added
- **AI 预标注功能**（PredictEngine）
  - 基于规则的自动标注
  - 预测结果高亮显示（🤖 徽章）
  - 支持时序平滑和HMM解码
- **预测方法标签**
  - 面板显示当前使用的预测方法
  - 支持手动修正预测结果
- **自动标签摘要**
  - 显示自动标签统计信息
  - 支持批量应用和撤销

### Changed
- 优化雷达图渲染性能
- 改进时间轴点击响应
- 优化批量修正的用户体验

## [0.4.2] - 2024-11-XX

### Added
- **Episode 级语义标注**
  - 操作结果（成功/失败/中止/部分）
  - 操作类型（抓取/推动/拉取/轻触等）
  - 难度等级（简单/中等/困难）
  - 备注字段
- **数据质量评分仪表盘**
  - 4维度评估（物理一致性、时序平滑度、完整性、覆盖率）
  - 综合评分和等级显示
  - 质量警告提示
- **统计摘要表格**
  - 类似 pandas DataFrame.describe()
  - 支持 count, mean, std, min, 25%, 50%, 75%, max

### Changed
- 面板样式优化
- 暗色模式支持
- 中英文切换优化
