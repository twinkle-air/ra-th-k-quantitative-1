# 导出权限失败的恢复

默认目录仍为使用者的桌面。服务进程没有该目录写权限时，所选目录可能存在但实际写入被拒绝。旧实现再次回退到桌面，造成同一路径重复失败。

当前保存顺序：所选目录 → 独立的项目exports目录 → 浏览器下载。直接保存成功才返回path；两目录都无法写入时返回download_required=true和path=null，前端通过原有下载接口重新校验分析并获取文件，不把文件生成失败或质控失败当成目录问题。桌面桥与Web共用保存逻辑。

实际8000端口请求已验证：桌面拒绝写入时，Excel成功回退至项目exports，返回fallback=true、download_required=false，生成文件存在。浏览器下载分支通过模拟双目录拒绝和下载接口测试，未将其标成已实际完成的浏览器下载。

备用保存会显示实际文件路径。浏览器下载仅提示已发起，用户须在下载列表确认完成；位置由浏览器设置或保存对话框控制，不能承诺自动写到桌面。可以通过“修改位置”选择其他已存在且可写的目录。不会修改Windows权限或要求管理员运行。

2026-10-03：57项回归测试通过；包含PNG/PDF/Excel、DOCX及可填写PDF模板的所选目录拒绝、两目录拒绝及同目录不重复写入场景。模板测试产生的字体编码警告属于既有PDF模板字体问题，不属于本次权限修复，未据此宣称模板字体已修正。

依据：Python PermissionError文档 https://docs.python.org/3/library/exceptions.html#PermissionError ；浏览器download行为 https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/a#download 。
