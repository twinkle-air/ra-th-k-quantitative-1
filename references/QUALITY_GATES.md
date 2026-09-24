# 可执行质量门

质量门输出三个总状态：

- `ready_for_quantification`：程序检查项未发现阻断或条件性问题；这不等于实验室认证。
- `conditional_result`：计算可以完成，但只能作为带限定条件的估算。
- `blocked`：不得输出定量结论，用户要求忽略警告也不能越过。

## 阻断规则

- `blocked_missing_live_time`：任一标准/样品谱缺少正的活时间；
- `blocked_missing_mass`：任一样品缺少正的净质量；
- `blocked_calibration_failure`：斜率非正或能量刻度 RMS 超过项目策略 0.5 keV；
- `blocked_empirical_profile_out_of_scope`：自定义源或非原始内置源试图启用旧五样品经验配置；
- `invalid_evidence`：保存结果、核数据或快照指纹不一致。

## 条件性规则

- 标准源证书标识或溯源确认不完整；
- 几何或基质未明确验证匹配；
- Ra/Th 衰变链平衡未确认，此时只报告子体等效活度；
- 目标峰均未超过 Currie 判定阈值，此时 `reportable_activity_bq_kg=null`；
- 多峰最大相对偏差超过项目策略阈值（默认 30%，不是国家标准限值）；
- 使用旧五样品经验配置，该结果不得作为独立验证证据。
- 刻度源谱缺采集日期/时间：参考日活度未能校正至测量时刻，只能输出条件性估算。

`estimated_activity_bq_kg` 是计算得到的数值，供复核；只有单核素状态为 `ready_for_quantification` 且检出时，`reportable_activity_bq_kg` 才有值。条件性、阻断或非检出均使可报告字段为 `null`。PNG/PDF/Excel 与 DOC/DOCX/PDF 模板中的正式结果字段只读取后者；模板若要展示估算值，可明确使用 `sample.ra_estimated_bq_kg` 等带 `estimated` 的占位符并注明条件。Web、桌面、CLI/MCP 导出均先验证快照，阻断状态禁止正式导出。

证书编号、溯源声明、几何/基质匹配和平衡状态来自用户输入，程序只记录并检查形式，**未独立核验证书或实物**。SHA-256 只能发现快照被改动，不能证明原始声明真实，也不是数字签名。

核素半衰期、换算系数、γ 线能量及发射概率采用 `assets/app/data/nuclear_data.json` 的项目数值；该表为每条数值记录了来源候选、版本线索和逐值核验状态。算法从同一表构造使用的核数据常数，防止证据表与计算硬编码漂移。`exact_value_verified=false` 表示尚未完成与当前权威评价的逐值比对，链接不是认证声明；尤其不能把项目沿用的 ⁴⁰K 半衰期和发射概率误称为最新 DDEP 推荐值。

当前 `counting_standard_uncertainty_bq_kg` 只覆盖样品与标准峰计数统计以及观测到的峰间离散。标准源活度、发射概率、质量、衰变修正、峰模型、效率拟合、几何重复性、基质自吸收和 K-40 干扰模型尚未形成完整预算，因此 `combined_measurement_uncertainty_available=false`。
