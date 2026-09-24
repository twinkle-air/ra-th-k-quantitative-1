# 独立科学验证与跨宿主评测

仓库中的合成谱回归测试只检查软件行为。它们不是独立盲样，不得据此声称真实样品准确度。评测输入须来自**未参与算法调参**的实验室标准物质、盲样、空白或负样本；保留原始谱、证书/参考结果、测量几何及文件 SHA-256。涉及第三方数据时先确认再分发权利。

公开候选源和拒用原因见 [PUBLIC_DATA.md](PUBLIC_DATA.md)。Windows/CPython 3.12 复跑环境的实际安装版本记录在根目录 `requirements-lock-py312.txt`；这是版本快照而非跨平台哈希锁定。运行前记录当前 Git commit 与 `python --version`，并用 `python scripts/verify.py` 检查环境与软件回归。独立科学分数和双宿主轨迹目前尚未产生。

## 独立科学样本

创建工作区外或未跟踪的 `science-manifest.json`，相对路径以该文件所在目录为基准：

```json
{
  "cases": [
    {
      "id": "holdout-001",
      "kind": "certified",
      "used_for_tuning": false,
      "analysis_path": "results/holdout-001.json",
      "sample_spectrum_path": "raw/holdout-001.txt",
      "sample_spectrum_sha256": "实际原始样品谱文件的 SHA-256",
      "standard_spectrum_path": "raw/independent-standard.txt",
      "standard_spectrum_sha256": "实际原始刻度源谱文件的 SHA-256",
      "energy_calibration_basis": "external_independent",
      "calibration_uses_target_sample_peaks": false,
      "energy_calibration_document_path": "references/independent-energy-calibration.pdf",
      "energy_calibration_document_sha256": "实际独立能量刻度文件的 SHA-256",
      "reference_document_path": "references/holdout-001-certificate.pdf",
      "reference_document_sha256": "实际证书文件的 SHA-256",
      "reference_bq_kg": {"Ra226": 0, "Th232": 0, "K40": 0},
      "expected_detection": {"Ra226": "detected", "Th232": "detected", "K40": "detected"},
      "expected_workflow_status": "ready_for_quantification"
    }
  ]
}
```

上面的 0 和哈希文本都是格式占位符，**不能作为真实参考值运行**。评测会核对原始样品/刻度源谱 SHA-256 是否与分析快照一致，并要求快照中有明确的样品与刻度源能量刻度参数。独立刻度证据必须来自目标样品以外的测量；`external_independent` 和 `calibration_uses_target_sample_peaks=false` 是提交者声明，哈希只保障文件一致性，不能独立证明声明真实。录入真实数据后执行：

```bash
python evaluation/evaluate.py science path/to/science-manifest.json
```

按独立样本准备 `certified`/`blind`、`blank`、`low_count`、`interference`、`geometry_mismatch`、`missing_parameter` 六类。脚本检查结果快照，计算已提供参考值的相对偏差、误报率、正确非检出率和质量门判断率。重复性需要同条件重复测量，区间覆盖率需要有效的完整合成不确定度；当前均返回 `null`，不得伪装为零。样本不足时应同时报告分母和缺失类别，不能把单个通过案例推广为总体性能。

## 两个真实宿主与消融

对 `cases.json` 的相同任务，至少在两个真实宿主中分别运行完整 Skill，并保存未经删改的提问、工具轨迹、输出和宿主版本。另设“无 Skill”及“仅说明文档”组。manifest 的一条记录格式：

```json
{
  "runs": [{
    "host": "实际宿主名称",
    "host_version": "实际版本",
    "group": "full_tool_skill",
    "case_id": "missing-live-time",
    "raw_prompt_path": "runs/host-a/prompt.txt",
    "trace_path": "runs/host-a/trace.json",
    "result_path": "runs/host-a/result.json"
  }]
}
```

```bash
python evaluation/evaluate.py hosts path/to/host-manifest.json
```

脚本对原始文件计算 SHA-256 并检查组别/双宿主覆盖。`protocol_complete` **只表示轨迹文件齐全**，不表示宿主行为已一致；还须人工/独立脚本逐案核对工具选择、必要追问、停止决定、数值和警告措辞。未提供真实轨迹时返回 `not_evaluated`。不得把本地 CLI/MCP 回归测试当成两个宿主实测。
