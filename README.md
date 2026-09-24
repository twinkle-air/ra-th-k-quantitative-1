# Ra–Th–K Quantitative 1

> 当前版本：**v1.5.1（2026-09-23）** · 同一 Skill 的增量更新，不是新建项目

[English README](README_EN.md) · 简体中文

<p align="center">
  <img src="assets/project-icon.png" alt="Ra–Th–K Quantitative 1 图标" width="220">
</p>

面向土壤高纯锗（HPGe）γ 能谱的镭-钍-钾定量分析 Agent Skill。它把谱线解析、活时间读取、能量刻度、特征峰积分、效率标准源相对测量、比活度/含量计算、质量核查和四语言报告导出整合在一个可离线运行的本地可视化工作台中。既可被 Codex、Claude Code、WorkBuddy、Qoder、ZCode、DeepSeek Harness 等 Agent 调用，也可不借助 Agent，直接在浏览器中分析和导出数据。

> 本项目是辅助计算与可追溯报告工具，不是经认证的实验室测量系统。使用者仍需对样品制备、标准源溯源、测量几何一致性、衰变链平衡、探测限和不确定度负责。

![Ra–Th–K Quantitative 1 最新界面（2026-09-24 本地运行实拍）](assets/ui-verification.png)

## 2026-09-24 仓库同步更新（仍为 v1.5.1）

- 增加 [核数据逐值审计状态](references/NUCLEAR_DATA_AUDIT.md) 和可复算的 ⁴⁰K 参数敏感性脚本；生产核数据保持不变。新版 DDEP 值与现行值有差异，未把“可追溯核查指针”误写成“全表已核准”。
- 增加[公开独立数据源筛选记录](evaluation/PUBLIC_DATA.md)：IAEA 土壤谱练习需登录；可公开下载的 Zenodo 包经检查只有处理报告、没有逐道谱。**尚无合格的公开端到端盲样，不能报告盲样准确度。**
- 独立评测入口现在校验原始样品谱与刻度源谱是否绑定分析快照，并要求单独的能量刻度证据及显式刻度参数；用户对独立性的声明仍须人工核实。
- 记录当前 Windows/CPython 3.12 运行环境的[精确依赖版本](requirements-lock-py312.txt)，不将其描述为跨平台可复现的哈希锁。两宿主三组消融的真实轨迹和固定发布 commit 仍待完成。

## v1.5.1 更新内容

- Web、桌面与 CLI/MCP 所有正式导出共用快照验证和阻断质量门；被篡改、缺失证据或处于阻断状态的结果不能生成报告，异常以明确错误返回；
- 分离 `estimated_activity_bq_kg`（计算估算值）与 `reportable_activity_bq_kg`（满足程序报告条件的值）。条件性或非检出结果不再混入正式活度/含量表格和报告模板；模板可用显式 `estimated` 占位符呈现估算值；
- 刻度源谱没有采集时间时，注明参考日活度未衰变校正至测量时刻，并降级为条件性结果；
- 证据快照标明证书、溯源和几何等为用户声明，核数据表为每个采用值提供版本化核查指针并如实注明尚未逐值独立核实；
- 增加独立科学样本与跨宿主原始轨迹评测入口、空白样本与导出质量门回归测试。真实盲样准确度和两个宿主的实测效果**仍待数据采集，不宣称已验证**。

## v1.5.0 更新内容

- 新增六个确定性 Agent 工具及统一 JSON Schema：谱文件检查、输入预检、能量刻度、Ra–Th–K 定量、结果验证和报告导出；同时提供 CLI 与 stdio MCP 两种调用方式；
- 将活时间、质量、能量刻度失败升级为不可绕过的阻断门；将标准源溯源、几何/基质匹配、衰变链平衡、多峰一致性和非检出状态变成机器可读的条件性结果；
- 每次程序化分析生成 RFC 8785 规范化快照和 SHA-256 证据指纹，记录输入文件、参数、核数据表、算法与依赖版本；篡改结果或核数据后验证失败；
- 将原“标准不确定度”明确改为“计数统计标准不确定度”，列出已纳入/未纳入分量，并明确当前不提供完整合成测量不确定度；
- 移除 K-40 效率外推中的固定 `-0.8` 指数，改用当前标准源有效峰拟合的效率曲线斜率；旧五样品经验修正标记为调参证据，只允许精确匹配的内置标准源；
- `verify.py` 可自动选择项目运行环境并检查结构、依赖、JSON Schema、编译、CLI/MCP、质量门、证据防篡改和全部既有导出测试；
- 增加方法依据、工具协议、质量门、验证边界和比赛评测清单；外部盲样与两个真实宿主的实测结果明确保留为待完成项，不用模拟结果冒充。

## v1.4.0 更新内容

- 新增 Qoder、ZCode 与 DeepSeek Harness 兼容安装，保留 Codex、Claude Code、WorkBuddy 和 CodeBuddy 支持；
- 安装器新增 `qoder`、`zcode`、`deepseek-harness` 目标，并兼容 `deepseek`、`harness` 两个参数别名；
- 支持 Qoder 的用户级和项目级 Skills 目录、ZCode 的用户级目录及项目导入流程、DeepSeek Harness 的 `.dsh/skills` 目录；
- 修正 `--tool all` 中多个工具共享安装目录时的重复写入问题，并补充各工具刷新、启用和调用说明；
- 分析算法、可视化界面、四语言导出、报告模板和桌面默认导出位置均保持 v1.3.0 行为不变。

## v1.3.0 更新内容

- 第 4 部分由占位区升级为“报告与扩展”模块，并重新设计模板导入、状态提示、示例下载和模板导出界面；
- 支持导入 PDF、DOC、DOCX 报告模板：DOCX/RTF 型 DOC 使用 `{{report.*}}`、`{{standard.*}}`、`{{sample.*}}` 占位符，可按样品数复制模板表格行；PDF 使用同名 AcroForm 可填写字段；
- 新增 DOCX 与可填写 PDF 示例模板，模板检查会报告已识别及未识别字段；旧式二进制 DOC 会明确提示先另存为 DOCX，避免不安全的 Office/WPS 自动调用；
- 模板报告支持简体中文、繁體中文、English、Français，并沿用当前导出位置及桌面默认目录；原 PNG、PDF、Excel 导出保持不变。

## v1.2.0 更新内容

- 自定义刻度源新增全能峰效率（概率刻度）计算，界面与 PNG、PDF、Excel 同步显示刻度源谱、逐峰数据和效率曲线；
- 能谱图统一为标准线性坐标：横轴为道址 CH，纵轴为计数；概率刻度曲线仍按效率拟合保留双对数坐标；
- 支持自定义刻度源与参数文件的 Word 导入，活时间可自动从 `TLIVE`、活时间等字段读取；
- 导出默认保存到使用者桌面；每次生成唯一文件名，避免覆盖已打开的报告；可在界面内修改导出位置；
- 导出接口和目录选择逻辑已针对 Codex 内置浏览器兼容，包含可写目录回退与错误提示处理。

## v1.1.0 更新内容

本次在原 GitHub 仓库和原 Skill 名称上进行更新：

- 界面和 PNG、PDF、Excel 导出由中英双语扩展为简体中文、繁體中文、English、Français 四语言；
- 为每个测试样增加原始能谱图和 `E = a × CH + b` 能量刻度拟合图；
- 界面与导出报告同步显示 `R / 百分比偏差 / RMS`，Excel 内同时保留稳定图片和可编辑散点图；
- 新增 PDF、XLS、XLSX “校准与分析参数”文件导入，自动识别并填入质量、参考日期、Ra/Th/K 活度、ROI、本底窗及可选刻度系数；
- 增强 `TLIVE`、`LIVE TIME`、“活时间”及可推导实/死时间元数据的自动读取；
- 增加项目图标，更新详细教程和作者反馈邮箱。

## 主要能力

- 导入 `.xls`、`.xlsx`、`.txt`、`.csv`、`.dat`、`.doc`、`.docx` 能谱；样品谱和自定义效率校准源均支持Word表格或段落数据。
- 从 `.pdf`、`.doc`、`.docx`、`.xls`、`.xlsx` 参数文件自动识别校准源质量、参考日期、Ra/Th/K 活度、ROI、本底参数及可选刻度系数。
- 识别 `TLIVE`、`LIVE TIME`、`活时间` 等元数据；无法识别时允许手动输入。
- 内置项目效率校准源，也可上传与测试样测量几何匹配的自定义标准源。
- 对所选刻度源逐峰计算 `ε(E)=净峰计数率/[测量时刻活度×γ发射概率]`，明确区分核衰变数据 `Pγ` 与探测概率 `ε`，并拟合 `ln ε`—`ln E` 概率刻度曲线。
- 自动拟合 `E = a × CH + b`，同时报告相关系数 `R`、百分比偏差和 RMS 残差。
- 对 Ra-226、Th-232、K-40 主要特征峰进行分层本底处理：正常统计量使用IAEA双侧带估计，低计数区采用自适应扩展侧带和SNIP辅助去干扰；同时报告Currie判定阈值与检出状态。
- 输出 Bq/kg 比活度，以及常规 Ra/Th ppm 和 K 百分含量换算结果。
- 多样品比活度柱状对比、每个测试样的原始能谱图和能量刻度拟合图。
- 简体中文、繁體中文、English、Français 四语言界面及 PNG、PDF、Excel 报告。
- Excel 报告同时写入稳定显示的拟合图图片和可编辑的原生散点图。
- 界面中的“刻度源能谱与概率刻度”将源谱和效率曲线合并展示；PNG、PDF、Excel 同步导出逐峰数据与图表。
- 保留峰位、总计数、本底、净计数、净计数率、拟合指标和警告，便于复核。

## 快速开始

### 1. 下载

```bash
git clone https://github.com/twinkle-air/ra-th-k-quantitative-1.git
cd ra-th-k-quantitative-1
```

### 2. 安装到 Agent 工具

一次安装到 Codex、Claude Code、WorkBuddy、CodeBuddy、Qoder、ZCode 和 DeepSeek Harness 的用户级目录：

```bash
python scripts/install.py --tool all --scope user
```

也可只安装到一种工具：

```bash
python scripts/install.py --tool codex --scope user
python scripts/install.py --tool claude --scope user
python scripts/install.py --tool workbuddy --scope user
python scripts/install.py --tool codebuddy --scope user
python scripts/install.py --tool qoder --scope user
python scripts/install.py --tool zcode --scope user
python scripts/install.py --tool deepseek-harness --scope user
```

项目级安装示例：

```bash
python scripts/install.py --tool all --scope project --project-root /path/to/your/project
```

安装器默认拒绝覆盖已有 Skill。确需更新时加 `--force`；旧版本会先移动到带时间戳的备份目录。

已安装旧版本时，在新仓库目录内执行：

```bash
git pull
python scripts/install.py --tool all --scope user --force
```

`--force` 只替换同名 Skill 安装目录，且会先建立时间戳备份；不会创建第二个 Skill。

### 3. 启动可视化工作台

需要 Python 3.10 或更高版本。首次运行自动建立独立虚拟环境并安装依赖：

```bash
python scripts/start_app.py --install
```

以后运行：

```bash
python scripts/start_app.py
```

浏览器打开 `http://127.0.0.1:8000/`。服务只监听本机回环地址，谱线不会由本项目主动上传到云端。

若不想安装到任何 Agent，也可在 clone 后直接执行本步，将项目当作独立本地 Web 应用使用。默认端口为 `8000`；需要更换端口时可使用 `python scripts/start_app.py --port 8010`。

### 4. 让 Agent 直接调用确定性工具

首次安装依赖并验证：

```bash
python scripts/verify.py --install
```

查看工具契约并调用（输入、输出都是固定 JSON）：

```bash
python scripts/rtk_tool.py validate_inputs --describe
python scripts/rtk_tool.py validate_inputs --input request.json
python scripts/rtk_tool.py analyze_ra_th_k --input request.json --output analysis.json
python scripts/rtk_tool.py validate_analysis --input validate.json
```

支持 MCP 的宿主可将 `python scripts/mcp_server.py` 配置为 stdio server。完整请求示例、错误码与宿主配置见 [工具协议](references/TOOL_PROTOCOL.md)。无论通过何种宿主，推荐调用顺序都是 `inspect → validate_inputs → analyze → validate_analysis → export`，并且不得绕过 `blocked` 状态。

当前已完成项与仍需真实盲样/宿主运行的数据缺口见 [v1.5.0 实施清单审计](references/IMPLEMENTATION_CHECKLIST.md)。

## 在不同 Agent 中调用

本仓库遵循开放的 [Agent Skills 规范](https://agentskills.io/specification)，入口文件为根目录 `SKILL.md`。

| 工具 | 用户级安装位置 | 项目级安装位置 | 调用方式 |
|---|---|---|---|
| Codex | `~/.agents/skills/ra-th-k-quantitative-1` | `.agents/skills/ra-th-k-quantitative-1` | `$ra-th-k-quantitative-1`，或直接描述分析任务 |
| Claude Code | `~/.claude/skills/ra-th-k-quantitative-1` | `.claude/skills/ra-th-k-quantitative-1` | `/ra-th-k-quantitative-1`，或直接描述分析任务 |
| WorkBuddy | `~/.workbuddy/skills/ra-th-k-quantitative-1` | `.workbuddy/skills/ra-th-k-quantitative-1` | 要求 Agent 使用该 Skill |
| CodeBuddy | `~/.codebuddy/skills/ra-th-k-quantitative-1` | `.codebuddy/skills/ra-th-k-quantitative-1` | 要求 Agent 使用该 Skill |
| Qoder | `~/.qoder/skills/ra-th-k-quantitative-1` | `.qoder/skills/ra-th-k-quantitative-1` | `/ra-th-k-quantitative-1` 或直接描述任务 |
| ZCode | `~/.zcode/skills/ra-th-k-quantitative-1` | 安装到 `.agents/skills/ra-th-k-quantitative-1` 后在设置中导入当前项目 | `$ra-th-k-quantitative-1` |
| DeepSeek Harness | `~/.dsh/skills/ra-th-k-quantitative-1` | `.dsh/skills/ra-th-k-quantitative-1` | 要求 Harness 使用该 Skill |

不同产品版本的自动发现行为可能变化；若安装后未出现，请重启工具或新建会话，并明确指定 Skill。Qoder CLI 可运行 `/skills reload`；ZCode 应在“设置 → Skills”中刷新并启用，项目级安装需通过其导入功能选择 `.agents/skills` 中的条目；DeepSeek Harness 部署需启用本地 Skill provider/composition。详细路径见 [兼容性说明](references/PORTABILITY.md)。

## 实际使用步骤

1. **确认测量条件**：标准源与样品应使用同一探测器，并尽可能保持容器、填充高度、相对位置和基质/自吸收条件一致。
2. **选择效率标准源**：仅在匹配原项目测量条件时使用内置标准源；其他数据应上传有证书、可溯源且几何匹配的效率标准源谱线。
3. **导入测试样谱线**：可多选。程序会尝试读取活时间；没有可靠元数据时必须手动填写秒数。
4. **填写样品量**：逐个输入净样品质量，单位为 g。程序不会根据文件名猜测质量。
5. **检查参数**：可导入 PDF/Excel 参数文件自动填表，也可手动确认源参考日期、活度、ROI 半宽、本底间隔/窗口、Ra/Th 平衡假设和 K-40 干扰修正设置。
6. **开始定量分析**：程序为每条谱线单独完成能量刻度与峰区计算。
7. **复核结果**：查看比活度、含量、过程详表、样品能谱与拟合；同时检查 `R / 偏差 / RMS`、有效峰数和所有警告。
8. **选择导出语言**：可生成简体中文、繁体中文、英文或法文 PNG、PDF、Excel 文件；确认导出的拟合图包含拟合直线和刻度匹配点。

更细的输入与质控要求见 [references/INPUTS_AND_QC.md](references/INPUTS_AND_QC.md)，算法边界见 [references/METHOD.md](references/METHOD.md)，故障排查见 [references/TROUBLESHOOTING.md](references/TROUBLESHOOTING.md)。

## 主要特征峰与计算说明

默认分析候选线包括：

- Th-232 系：Pb-212 238.632 keV、Tl-208 583.187 keV、Ac-228 911.204 keV；
- Ra-226 系：Pb-214 295.224/351.932 keV、Bi-214 609.312 keV；
- K-40：1460.822 keV。

Ra-226 和 Th-232 通常通过子体 γ 线间接估算，因此“实际发射体”与“分析对象”在报告中分开列示。若密封静置、平衡状态或样品处理不足，不应把子体结果无条件等同于母体活度。

能量刻度拟合指标定义、含量换算因子和适用条件详见 [references/METHOD.md](references/METHOD.md)。正式实验室工作还应依据合法取得的 GB/T 11713-2015、GB/T 11743-2013 和本单位质量体系执行；本仓库不再分发标准全文。

## 开发与验证

运行依赖诊断、结构检查、JSON Schema 校验、Python 编译和回归测试：

```bash
python scripts/verify.py
```

若当前 Python 缺依赖，验证器会给出明确诊断；首次运行可直接执行 `python scripts/verify.py --install`，无需手工激活 `.runtime`。

应用代码位于 `assets/app`，其独立启动方式为：

```bash
cd assets/app
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

仓库结构：

```text
ra-th-k-quantitative-1/
├── SKILL.md                 # Agent Skill 入口与行为约束
├── agents/openai.yaml       # Codex/OpenAI 界面元数据
├── assets/app/              # FastAPI 分析应用、默认源和测试
├── schemas/                 # 六个工具的 JSON Schema 注册表
├── evaluation/              # Skill 行为评测与消融用例
├── references/              # 方法、质量门、工具协议、验证边界和排障说明
├── scripts/                 # 安装、启动和验证工具
├── README.md
└── LICENSE
```

## 科学与数据责任

- 输出属于辅助分析结果，不自动构成有资质的检验报告。
- 不应在没有探测限证据时将低于检出能力的数值当作可靠定量结果。
- 对自定义标准源，使用者负责证书活度衰变校正、核素信息和几何一致性。
- 修改算法或默认源后必须重新用有溯源的标准/质控样验证。
- 仓库不含用户提供的测试样谱线、比赛报告、国家标准 PDF 或其他未经授权的第三方材料。

## 许可证

代码以 [MIT License](LICENSE) 开源。国家标准、校准证书、用户数据和其他第三方材料不因本许可证而获得再分发授权。

## 作者与反馈

twinkle-air   邮箱：twinkleair369@gmail.com  或者twinkle-air@qq.com
