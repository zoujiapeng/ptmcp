# HANDOFF — 换窗口/换人接手看这里

最后更新：2026-10-21（commit 见 `git log -1`）

## 一、这套东西是什么

`ptmcp` = 让 agent **在后台**（不抢焦点、不点鼠标、不弹对话框）操控
Cisco Packet Tracer 8.0 的 MCP + CLI：建图、连线、配 IOS、读回配置、断言、自动修、存 `.pkt`、截图。

- 仓库：https://github.com/zoujiapeng/ptmcp
- 本机路径：`C:\Users\zou\八爪鱼下载\pt-mcp`
- PT：`C:\Program Files\Cisco Packet Tracer 8.0`（8.0.0.0212）
- PT 侧执行器：`extensions\MCPBuilder\V5.2.pts`（来自 packet-tracer-mcp，MIT）
- 邮箱：`%LOCALAPPDATA%\packet-tracer-mcp\bridge\`（req_*.js / res_*.txt / alive.txt）

## 二、已实测通过（可直接用）

```powershell
cd C:\Users\zou\八爪鱼下载\pt-mcp
python -m ptmcp bootstrap      # 找 PT + 装 .pts（纯文件操作，无需 GUI）
python -m ptmcp start          # 没开就拉起 PT，等引擎上线（冷启动约 4s）
python -m ptmcp status         # 画布设备/链路
python -m ptmcp build specs\campus.json   # 15 设备/14 链路，建图+全绿+断言+存盘
python -m ptmcp show S1 run|vlan|vtp|interfaces|mac
python -m ptmcp term S1                     # 终端 prompt/mode
python -m ptmcp run S1 "enable" "conf t" "hostname X" "exit"
python -m ptmcp asserts specs\campus.json
python -m ptmcp fixloop specs\campus.json   # assert→修→再断言
python -m ptmcp precheck specs\x.json --fix # 建图前预检
python -m ptmcp pdu-ping H1 H2              # 仿真真 ping（同一 VLAN 已验证通）
python -m ptmcp shot C:\pt\x.png            # PrintWindow 截图，无输入
python tests\headless.py                    # 冷启动全流程（零 computer use）
```

已验证的关键事实：

| 项 | 结果 |
|---|---|
| 冷启动无人值守 | 4.3–4.4s 引擎上线，两次一致 |
| 15 设备/14 链路 | `allUp=True`，`asserts 41/41`（campus 曾达） |
| 终端 | `run()` 回传每条命令后的 prompt（`S1(config)#`→`(config-if)#`…），`hostname` 真生效 |
| PDU ping | `H1→H2 ok=true`；能指出丢包设备（`R1:dropped`） |
| 弹窗 | `fileSaveAs` 覆盖、`fileNew()` 都会冻引擎 → 已用临时名+`fileNew(false)` 规避 |
| 两个竞品扩展 | **不能共存**：装 `cisco-pt-mcp.pts` 后我们的模块停止轮询；移除后 4s 恢复 |

## 三、已知未完成（下一窗口从这里接手）

### 1) campus 跨 VLAN/跨路由 ping 仍失败（优先级最高）

```
PC11 -> PC12 : ok=true   ✅
PC21 -> SRV1 : ok=false  ❌ R1:dropped
PC11 -> PC41 : ok=false  ❌ R2:dropped
```

已修：`SRV1` 网段写错（`10.30.0.0/24` → `10.31.0.0/24`，它挂在 `R1 Gi0/2.30`）。
未修：`R1`/`R2` 的**子接口 IP 或 OSPF 是否真的下发**。

排查顺序（建议）：

```powershell
python -m ptmcp show R1 run | Select-String "GigabitEthernet0/0.10|ip address|encapsulation|router ospf|network"
python -m ptmcp show R2 run | Select-String "GigabitEthernet|ip address|router ospf"
python -m ptmcp show R1 interfaces      # 看 g0/0、g0/1、g0/2 是否 up
python -m ptmcp pdu-ping R1 PC11        # 从路由器发起，定位是转发还是路由表问题
```

怀疑点：`build()` 的 CLI 阶段对**路由器**仍可能丢命令（开关正常）。若 `show R1 run` 里
没有 `.10/.30` 子接口或没有 `ip address`，就把 CLI 改成**分块发送 + 每块后 sleep 0.3s**，
或对路由器用 `term.run()`（逐条回传 prompt）而不是一次性 `enterCommand` 批量。

### 2) borrow 的 ACL/NAT 只到 Python 层

`ptmcp/borrow.py` 里 `acl_cli/nat_cli/hardening_cli/port_security_cli` 可用，但只有 `vlan_cli`
接成了 MCP 工具（`pt_borrow_vlan`）。若要补齐：给 `server.py` 各加一个 tool，参数用 JSON 字符串。

### 3) PT 8 的 3560 三层交换配不上

`switchport` 命令在 3560 端口上不被接受（`no switchport` 可以）。核心改用 2911 单臂路由绕过。
若要支持 MLS，需要另找方法（或确认 PT 9 是否正常）。

## 四、踩过的坑（别重复）

1. **不要读 `getIpcTerminalLine().getMode()` 来"探测模式"** —— 控制台未初始化时读它会把控制台弄坏，
   之后 `enterCommand` 全部静默失效（表现为：`hostname` 不生效、配置全丢、所有 prompt 变空）。
   正确做法：只用 `enterCommand("!", "global")` 这个 PTBuilder 老技巧。
2. **交换机↔交换机必须交叉线（8101）**，否则端口永不起来（红线）。
3. **冷启动要等**：`isBooting()` 变 false 之后 CLI 才可靠；PDU 还需要实时模式再等几秒（ARP）。
4. **仿真模式会污染后续操作**：PDU 用完必须 `setSimulationMode(false)`。
5. **`fileSaveAs` 目标已存在 → 弹覆盖框 → 引擎冻死**；`fileNew()` 无参数同理。
6. 保存后 PT 标题栏显示临时文件名（`*.tmp.pkt`），磁盘上的 `.pkt` 是对的。

## 五、下一窗口开场白（可直接粘）

> 接手 `C:\Users\zou\八爪鱼下载\pt-mcp`（github.com/zoujiapeng/ptmcp）。先读 `HANDOFF.md`。
> 现在 campus 拓扑 `PC21→SRV1`、`PC11→PC41` 的 PDU ping 失败（R1/R2 dropped），
> 先按 HANDOFF 第三节排查 R1/R2 子接口与 OSPF 是否真正下发；修好后用
> `python tests\_pdu_final.py` 复验三条 ping 全 PASS，再更新 README 并推 GitHub。
