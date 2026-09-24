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
