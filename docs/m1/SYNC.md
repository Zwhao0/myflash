# M1 GitHub 同步回执

PASS：权威服务器源提交 c50e53a8e8e70ae83c54b14841b69b397b18e001 已同步到GitHub提交 5899c098345a4b96c75970db8a18a6ff7ce86930；文件树 734ba0c4244064c4fad632c0d21eb06d5784fde1 完全相同，17个变化blob逐一匹配，完整树包含43个文件，main回读匹配。服务器离线，本机仅中转服务器Git快照，不作为开发源。公开回执数据见SYNC.json。

使用GitHub connector建立提交，双方commit/history不同；核验全部文件树，不声称提交历史相同。以main旧head租约及非force更新，未覆盖无关提交。当前回执/STATUS追加来自服务器下一提交，也需再次匹配tree；其最终双方SHA/tree写入服务器.git/m1-sync-final.json避免自引用。原始实验目录、venv/wheel depot、服务器私有说明均未上传；上传前按私有说明逐值扫描地址/凭证及实际GPU UUID。

M0原有两份文档地址已从当前文件脱敏；既有Git历史未重写，旧历史/旧diff的地址隐私不能由本轮当前文件扫描保证。未上传连接凭证。本轮M1结束；M2 NOT_RUN。
