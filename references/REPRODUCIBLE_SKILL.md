# 本地复跑与交付边界

运行 `python scripts/start_app.py --install` 准备依赖；有网络时完成安装，离线机器须提前准备与目标 Python/平台一致的 wheel 包并通过 `pip install --no-index --find-links <wheel目录> -r assets/app/requirements.txt` 安装。版本快照 `requirements-lock-py312.txt` 只适用于对应环境，不能宣称跨平台离线可用。

运行 `python scripts/verify.py`，然后 `python scripts/reproduce_skill.py --output <新的绝对目录>`。复跑脚本生成自制合成刻度源、样品、缺活时间样品，保存 SHA-256、完整请求与原始确定性结果，以及四语言 PNG/PDF/Excel。正常案例预期 ready_for_quantification；缺源定值和缺活时间案例预期 blocked。证书标识仅为合成测试声明，绝不是真实认证。

不依赖重新分发用户样品或比赛数据；内置标准源的原始公开许可仍待补，默认数据的 MIT 权利不能由本复跑推导。合成复跑不是独立盲样验证或宿主效果实验。

Codex：按 PORTABILITY.md 安装，在全新会话明确指定此 Skill 和生成的 normal-request.json。CLI 用 `python scripts/rtk_tool.py validate_inputs --input <request>`；MCP 同样六工具。真实宿主原始会话、模型、权限、工具轨迹和人工判分须另存；本仓库脚本的结果不能代替它们。

本地工作台仅支持回环地址，不支持作为公网服务。单上传文件上限20 MiB，请求总上限64 MiB；多文件超限须拆批。导出仅向已存在的本机目录写入，不覆盖现有报告；权限失败明确报错或提示回退位置。不要给宿主不必要的系统目录写权限。端口占用时选新的本地端口；缺依赖时修复环境，不绕过质量门。

发布冻结须记录 Git commit、工作区是否干净、依赖/宿主版本、fixture_manifest.json 与原始输出。未提交的工作目录不是已冻结发布版本；本轮不自动提交或推送。
