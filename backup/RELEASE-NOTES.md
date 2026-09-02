# Boot116 开发备份（未完成安装）

此 Release 用于备份研发源码、二进制和离线恢复材料，不是可用 macOS VM 产品。

- 当前结果：ARM64 macOS 26.6 / 25G72 到达 Recovery 启动选项。Boot116 正在验证图形修复，尚未证明进入安装器。
- 原生产宿主机和本机 Mac 不执行构建、安装或测试。恢复只能在新的隔离 Linux x86_64 VM 内进行。
- `qemu-boot116-linux-x86_64.tar.zst`：本次实际编译的 QEMU 和构建记录。
- `linux-runtime-libraries.tar.zst`：运行时库备份，不应直接解压覆盖系统目录；不等价于完整离线安装包。
- `research-and-helper-tools.tar.zst`：研究源码及已有辅助工具快照，含历史方案，不应全量执行其中脚本。
- `macos-26.6-restore-materials.tar.zst`：离线恢复输入和派生材料，不含正在运行的 Boot116 可写磁盘，不含个人 SSH / GitHub 凭据。
- `UniversalMac_26.6_25G72_Restore.ipsw.part-*`：原始安装恢复包分片，按文件名顺序合并；SHA-256 应为 `a8d59bdec11a16f704c1a41edc86461c77e71c790ac834a05266b9670287142c`。
- 各组 SHA256SUMS 随制品上传。**资产列表中没有的文件不代表已上传。上传仍在进行时不能当作完整备份。**

仓库为私有仓库；请勿把含恢复材料的开发备份擅自转为公开分发。
