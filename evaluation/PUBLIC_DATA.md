# 公开独立数据源筛选（2026-09-24）

目标是同一测量体系的**逐道原始样品谱、原始刻度源谱/独立能量刻度、采集时间、质量、几何和独立参考值**，且未用于本项目五样品经验调参。只有论文中的 Bq/kg 表，不能让程序重跑完整峰积分链；认证物质的参考值也不能和别的仪器谱任意拼接。

| 数据源 | 实际核查 | 当前判定 |
|---|---|---|
| [IAEA TERC-2022-01/02，Sample 07 土壤谱练习](https://analytical-reference-materials.iaea.org/previous-proficiency-tests) | IAEA 明确说明有可下载土壤能谱和练习结果，但其[数据门户](https://curem.iaea.org/ptreporting/)要求登录；未取得原始文件、条件和使用许可。 | 最优先申请/取得；目前不可运行，不能填造参考值。 |
| [IAEA-375 认证土壤参考物质](https://analytical-reference-materials.iaea.org/iaea-375) | 有 ²²⁶Ra、²³²Th、⁴⁰K 参考活度；公开页面没有与本项目匹配的原始逐道谱和刻度源谱。 | 适合作为未来自测留出样的参考物质；网页本身不能完成软件盲测。 |
| [Zenodo 8268875，埃塞俄比亚土壤 HPGe 数据](https://zenodo.org/records/8268875) | 公开包 MD5 `99ccd0aeb3a0acf8907c58026fdedb5a`，实际核查 ZIP：11 份 `ERTL-SS*.PDF`，是峰定位/面积/效率/活度等处理报告，**非逐道原始谱**。 | 可作为独立峰级结果的交叉阅读，不足以进行本项目端到端谱分析/盲测；数据许可栏未给出可确认的复用许可，不再分发原文件。 |
| [Mendeley Saveh Soil Dataset](https://data.mendeley.com/datasets/23kffjx8k2/1) | 描述列出活动浓度、峰信息及计数时间，未证明含逐道原始谱、标准谱和完整几何。 | 待下载核查；不能仅凭“raw data”字样入评测。 |
| [MCNP 模拟土壤谱](https://github.com/haipn91/hpge-soil-gamma-41) | 公开说明为 MCNP 模拟。 | 可做软件压力/干扰测试，不得冒充实测独立准确度。 |

当前**没有合格可直接运行的公开端到端盲样数据包**，所以 `evaluation/evaluate.py science` 暂无真实成绩。后续取得 IAEA 登录权限或可合法使用的实验室留出样时，先冻结算法、散列原始文件，并将参考值与谱文件的同一样本、同几何关系逐一核查；刻度必须由独立数据建立，不能用待识别的同一组 Ra/Th/K 峰自我证明。
