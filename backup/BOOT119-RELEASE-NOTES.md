# Boot119：ARM64 macOS Tahoe 安装欢迎界面已验证

2026-09-03 03:09:33（北京时间），在独立 x86_64 Linux 验证 VM 中，
QEMU TCG + Reims PVG / metal2vulkan + Mesa lavapipe 已显示真实 macOS Tahoe
26.6 / 25G72 安装欢迎界面。内核为 RELEASE_ARM64_VMAPPLE；InstallAssistant
为 Mach-O arm64。成功范围是进入安装界面，**并非已完成磁盘安装或安装后启动**。

开发分支：`dev/boot119-installer-20260903`。完整源码快照、脚本、回归用例、
README、已知问题、架构证据及截图在该分支中；第三方许可证保留。

后台任务逐项上传并核对远端 SHA-256 和大小，日志最终出现 COMPLETE 才表示
本清单全部完成。Release 先创建，资产会陆续出现，不能把空 Release 当作完成。

- `source-boot119.tar.gz`：本次固定 commit 的完整 Git 源码快照。
- `qemu-boot119-linux-x86_64.tar.gz`：成功运行的二进制、构建配置、源码差异和 Rust 源码快照。
- `linux-runtime-boot119.tar.gz`：验证 VM 当前运行库、lavapipe 与验证层依赖；仅供恢复参考，禁止直接覆盖生产系统。
- `boot119-test-build-evidence.tar.gz`：对应版本的有限构建和回归日志。
- `boot119-environment.tar.gz`：验证 VM 发行版、包版本、动态库及文件清单。
- `screen-installer-first.png`、`boot119-installer-acceptance.md`：真实 QMP 截图及证据记录。
- `BOOT119-SHA256SUMS`：全部上述资产的 SHA-256。

不包含正在运行的磁盘、Apple 固件/恢复包、个性化票据、认证状态、密钥、
私有反汇编或生产宿主机配置，因此不是完整离线可启动交付包。
旧分支与旧制品不覆盖；Boot119 不因备份而停止。本次没有进行硬件 GPU 测试。
