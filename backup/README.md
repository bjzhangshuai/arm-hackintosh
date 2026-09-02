# 开发备份

## 2026-09-03：Boot119 安装界面成功检查点

新的开发分支为 `dev/boot119-installer-20260903`，Release 标签为
`backup-20260903-boot119`。不覆盖旧分支，不 force-push。
本次保存最新源码、脚本、回归用例、截图、验收结论、成功二进制和对应测试/构建记录。
详细边界见 [Boot119 Release 清单](BOOT119-RELEASE-NOTES.md)。

后台控制器 `push-boot119-background.sh <固定commit>` 使用本机已授权的 GitHub
账户推送，并仅在隔离验证 VM 内打包已有文件；不会编译、测试、安装或停止 VM。
状态落在被 Git 忽略的 `release-staging/backup-20260903-boot119/`：
`CODE_PUSHED` 表示代码已核对远端 commit；`COMPLETE` 表示所有本次制品均已核对
远端 SHA-256 和大小；`RESULT` 记录退出码。仅启动后台任务不代表上传已完成。

新增 APFS 格式化工具包含实际修改后的源码及许可证，不以空 gitlink 代替源码。
其原始 Git 元数据保存在本地忽略目录下，上游 commit 为
`3721463ba7f539e532907bc1d10ed5b9a97d0449`。
不上传运行中的磁盘、Apple 操作系统材料、认证票据或生产配置。

## 2026-09-02：历史 Boot116 备份记录

目标仓库：`git@github.com:bjzhangshuai/arm-hackintosh.git`

开发分支：`dev/backup-boot116-20260902`。不覆盖其他分支，不 force-push。

## 范围与来源

1. 当前代码以隔离验证 VM 的 `/home/macvm/src/macvm` 为准；第三方源码含未提交修改，而不只是上游版本。
2. 本机 `/Users/jansurezhang/src/macvm-arm64-x86` 的最新 `BLOCKERS.md`、截图及后续收集的历史证据作为补充。
3. 构建产物、系统安装材料与大日志不进入普通 Git 对象；通过单独 Release 制品和 SHA-256 清单备份。
4. 不复制 `.ssh`、个人登录凭据、私钥、生产 VM 磁盘、生产服务或穿透配置。上游 QEMU 自带公开测试密钥夹具不是个人凭据。
5. 当前运行中的 Boot116 可写磁盘不做直接文件拷贝，避免把不一致快照误当作可恢复备份；不会为备份强行停止它。

## 上传状态

- Git 源码快照：正在整理并推送本分支，最终以远端 commit 为准。
- GitHub Release：当前本机 `gh` 未登录，待授权后上传；**此时不能称安装包已经上传完成**。
- 已确认隔离 VM 原始 IPSW：`/home/macvm/macos-restore/26.6/UniversalMac_26.6_25G72_Restore.ipsw`，19,772,077,142 字节。
- 个性化签名票据、运行时 EAN/keychain 状态等不能混入公开源码；另行核对仓库可见性及敏感内容后处理。
- 第三方编译缓存、重复派生文件及挂载中的文件系统不作为源码复制；保留来源与恢复材料清单。

## 恢复原则

源码已经包含补丁，不要再把 `patches/` 全量应用一次。Git 快照不包含上游 `.git` 元数据；
需要原始历史时应在独立目录按锁定提交重新检出，并比较补丁/源码清单，不能覆盖当前树。

只在新的专用 Linux x86_64 测试 VM 内恢复。不得运行历史生产宿主机操作脚本。
当前 Boot116 二进制 SHA-256：

```text
80d19c41e8e8e9be5a4f662e7f303b770956e14367516634467d5c3388f1ee34
```

读取 `environment/` 中的实际配置、依赖和来源信息后再构建。恢复材料上传完成前，
该仓库是代码与证据备份，**不是完整离线可启动的交付包**。
