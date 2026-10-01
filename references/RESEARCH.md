# v1.5.0 设计依据

以下公开资料用于确定实现边界，检索日期为 2026-09-22：

- Agent Skills Specification：Skill 目录、`SKILL.md` 与渐进披露资源结构，https://agentskills.io/specification
- Model Context Protocol tools 规范（2025-11-25）：工具输入/输出 Schema 与结构化内容，https://modelcontextprotocol.io/specification/2025-11-25/server/tools
- JSON Schema Draft 2020-12，https://json-schema.org/draft/2020-12
- NIST FIPS 180-4：SHA-256，https://csrc.nist.gov/pubs/fips/180-4/upd1/final
- RFC 8785：JSON Canonicalization Scheme，https://www.rfc-editor.org/rfc/rfc8785.html
- JCGM 100:2008（GUM）：测量不确定度表达，https://www.bipm.org/en/doi/10.59161/jcgm100-2008e
- VIM 2.26/2.33：测量不确定度与不确定度预算术语，https://jcgm.bipm.org/vim/en/2.26.html 和 https://jcgm.bipm.org/vim/en/2.33.html
- ISO 11929-4:2022：电离辐射测量判定阈/探测限框架，https://www.iso.org/standard/84497.html
- IAEA-TECDOC-1401：γ谱实验室分析与质量控制，https://pub.iaea.org/MTCD/Publications/PDF/te_1401_web.pdf

这些资料支持“确定性工具契约、可执行质量门、可追溯身份链和保守不确定度命名”的设计。项目策略阈值（例如能量刻度 RMS 0.5 keV、多峰偏差 30%）不是从这些文献中冒充为强制标准，而是明确标为本项目策略，正式应用需由实验室验证并配置。

## 2026-09-27 多样品图表与状态显示核查

- 一手实现依据：`assets/app/app/services/quality.py` 将 `ready_for_quantification`、`conditional_result`、`blocked` 分开，并分别提供 `reportable_activity_bq_kg` 与 `estimated_activity_bq_kg`；`references/QUALITY_GATES.md` 限定后者仅供过程复核。
- 缺陷定位：旧界面直接输出英文状态码；旧图表仅读取 `reportable_activity_bq_kg`，当多样品均为条件性/阻断时会出现有坐标轴但无柱形。PNG/PDF/Excel 图表沿用相同字段，因此也需同步修复。
- 设计取舍：状态码在机器记录中保持原样，四语言只改变用户可见标签；图表把已检出的条件性正值单列为浅色“非正式估算”，与深色正式值区分。阻断、未检出和非正值不伪装成零或可报告活度。这是**呈现层的区分**，并非新测量方法或科学准确度验证。既有 ISO 11929-4:2022 与 IAEA-TECDOC-1401 只作为判定/质控边界背景，不将具体配色和图表样式归于标准要求。

## 2026-09-27 内置刻度源质控措辞核查

- 用户提供的《土壤监测效率校准源信息.docx》列有编号 `7NTR-1024`、2015-01-25 参考日期、Ra/Th/K 活度、扩展不确定度及定值方法。这些是项目源资料；仅凭该文件不能判定原始证书不存在，也不能把编号擅自认定为证书编号。资料归属地质调查局是用户提供的说明，程序未独立鉴别出具机构或真伪。
- JCGM VIM 2.41（BIPM，https://jcgm.bipm.org/vim/en/2.41.html）将计量溯源定义为测量结果经文件化、不中断的校准链关联至参考，并由各环节贡献不确定度。来源说明或机构名称本身不等于已核准完整溯源链。
- 因此内置文件经内容校验后使用中性代码 `conditional_bundled_standard_documentation_unverified`，说明软件未独立核验原始定值和计量溯源文件，不再断言“缺少证书”；自定义文件在证书标识及溯源声明不完整时保留 `conditional_unverified_standard`。CLI/MCP 不能只凭调用方填写 `source_kind=bundled` 获得内置源分支。

# 2026-10-01 十样品运行复核补充

查阅NIST RPD-P-23 2024年4月版本：https://www.nist.gov/system/files/documents/2024/04/25/Procedure23v110.pdf 。第2页列出多种核素的刻度源，第27页要求检查能量刻度稳定性，发生偏移时重新刻度；第25页说明几何与自吸收修正条件。这支持对异常能量匹配及几何条件进行复核，不支持将60个候选峰视为规范阈值。

本次实际谱发现最强35候选截断会遗漏混合谱中的弱Ra/Th/K峰，进而产生偶然一致的错误刻度。仅扩容候选池的第一次复测又发现宽容差先排名可能排除正确假设。最终扩大至检测器函数已有60候选池，并在假设排名阶段即采用不超过0.5 keV的一致性容差，保留原最终RMS门。具体旧/新快照在用户本地分析报告文件夹；未复制用户原谱至公开仓库，未推送。工程修复与已有样品回归不构成独立参考值准确度验证。
