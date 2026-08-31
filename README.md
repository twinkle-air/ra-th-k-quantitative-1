# Ra–Th–K Quantitative 1

> 当前版本：**v1.3.0（2026-08-31）** · 同一 Skill 的增量更新，不是新建项目

<p align="center">
  <img src="assets/project-icon.png" alt="Ra–Th–K Quantitative 1 图标" width="220">
</p>

面向土壤高纯锗（HPGe）γ 能谱的镭-钍-钾定量分析 Agent Skill。它把谱线解析、活时间读取、能量刻度、特征峰积分、效率标准源相对测量、比活度/含量计算、质量核查和四语言报告导出整合在一个可离线运行的本地可视化工作台中。既可被 Codex、Claude Code、WorkBuddy 等 Agent 调用，也可不借助 Agent，直接在浏览器中分析和导出数据。

> 本项目是辅助计算与可追溯报告工具，不是经认证的实验室测量系统。使用者仍需对样品制备、标准源溯源、测量几何一致性、衰变链平衡、探测限和不确定度负责。

![Ra–Th–K Quantitative 1 最新界面](assets/ui-verification.png)

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

一次安装到 Codex、Claude Code、WorkBuddy 和 CodeBuddy 的用户级目录：

```bash
python scripts/install.py --tool all --scope user
```

也可只安装到一种工具：

```bash
python scripts/install.py --tool codex --scope user
python scripts/install.py --tool claude --scope user
python scripts/install.py --tool workbuddy --scope user
python scripts/install.py --tool codebuddy --scope user
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

## 在不同 Agent 中调用

本仓库遵循开放的 [Agent Skills 规范](https://agentskills.io/specification)，入口文件为根目录 `SKILL.md`。

| 工具 | 用户级安装位置 | 项目级安装位置 | 调用方式 |
|---|---|---|---|
| Codex | `~/.agents/skills/ra-th-k-quantitative-1` | `.agents/skills/ra-th-k-quantitative-1` | `$ra-th-k-quantitative-1`，或直接描述分析任务 |
| Claude Code | `~/.claude/skills/ra-th-k-quantitative-1` | `.claude/skills/ra-th-k-quantitative-1` | `/ra-th-k-quantitative-1`，或直接描述分析任务 |
| WorkBuddy | `~/.workbuddy/skills/ra-th-k-quantitative-1` | `.workbuddy/skills/ra-th-k-quantitative-1` | 要求 Agent 使用该 Skill |
| CodeBuddy | `~/.codebuddy/skills/ra-th-k-quantitative-1` | `.codebuddy/skills/ra-th-k-quantitative-1` | 要求 Agent 使用该 Skill |

不同产品版本的自动发现行为可能变化；若安装后未出现，请重启工具或新建会话，并明确指定 Skill。Codex 和 Claude Code 的路径与调用方式分别参见其官方 [Codex Skills 文档](https://learn.chatgpt.com/docs/build-skills) 和 [Claude Code Skills 文档](https://code.claude.com/docs/en/skills)。

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

运行结构检查、Python 编译和回归测试：

```bash
python scripts/verify.py
```

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
├── references/              # 方法、输入质控、兼容性和排障说明
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
