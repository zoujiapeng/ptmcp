# ptmcp — 后台操控 Cisco Packet Tracer 的 MCP（面向 agent）

在**不抢焦点、不弹任何对话框**的前提下，让 agent 建拓扑、把链路画成绿的、跑 CLI、存 `.pkt`。
在 PT 8.0.0.0212 上实测通过；设计目标是一台陌生电脑上装好 PT 后，agent 拿到本仓库就能干活。

```
pip install -e .
python -m ptmcp bootstrap      # 安装 PT 侧脚本模块并自检
python -m ptmcp status
```

MCP 客户端接入：

```
claude mcp add --scope user --transport stdio ptmcp -- python -m ptmcp serve
```

## 它解决的问题

| 症状 | 原因 | 本仓库的做法 |
|---|---|---|
| 链路一直是红的 | 交换机↔交换机用直通线，PT 判 MDI/MDX 错 | `catalog.pick_cable()` 自动选交叉线（8101），主机/路由接交换机用直通（8100） |
| 脚本引擎卡死、请求全超时 | `fileSaveAs()` 覆盖已存在文件 → "Overwrite File?" 模态框阻塞引擎 | `pt.save()` 先删目标、存到唯一临时名、再 `os.replace` |
| `fileNew()` 弹"是否保存" | 默认带提示 | 统一用 `fileNew(false)` |
| `addDevice` 后链路/端口对象失效 | `fileNew()` 会让缓存的工作区句柄失效 | 先 `fileNew(false)`，再取工作区句柄 |
| 拿不到 CLI 输出 | PT 的 IPC 不暴露终端回显（`getCurrentHistory().history` 只有命令串） | `pt_ping()` 在设备 CLI 里真跑 ping（人打开 CLI 能看到 Reply），可达性用 `pt_verify_l2()` 做机器判定 |

## 工具（MCP）

| tool | 作用 |
|---|---|
| `pt_status()` | 画布上的设备/链路 + 引擎是否在轮询 |
| `pt_new()` | 清空画布（无对话框） |
| `pt_build(spec_json, save_path)` | 建图：设备 / 链路（自动选线）/ IP / CLI，并逐条报链路 up/down |
| `pt_wait_links(spec_json, timeout_s)` | 轮询到全部链路 up（STP 收敛需要几秒到几十秒） |
| `pt_cli(device, commands)` | 在 IOS 设备上执行 CLI |
| `pt_ping(source, target_ip, count)` | 在设备 CLI 里执行 ping |
| `pt_save(path)` | 存 `.pkt`，永不弹覆盖对话框 |
| `pt_run_js(code)` | 逃生口：直接跑 JS（结尾 `throw new Error(text)` 回传） |

拓扑规格：

```json
{
  "devices": [{"name": "S1", "model": "2950T-24", "x": 260, "y": 140},
              {"name": "PC0", "model": "PC-PT", "x": 150, "y": 400}],
  "links":   [{"a": "S1", "a_port": "FastEthernet0/1",
               "b": "PC0", "b_port": "FastEthernet0"}],
  "ips":     [{"device": "PC0", "port": "FastEthernet0",
               "ip": "192.168.2.1", "mask": "255.255.255.0"}],
  "cli":     {"S1": ["vlan 2", "name VLAN2", "exit"]},
  "save":    "C:\\pt\\lab.pkt"
}
```

`links[].cable` 可省略（`auto`）：交换机组之间自动交叉、其余直通。

## 通道原理

PT 的 Script Module 是唯一能在 PT 进程内跑代码的正规入口。本仓库复用
[MCP-Packet-Tracer](https://github.com/Mats2208/MCP-Packet-Tracer) 的 `V5.2.pts`
（MIT，bootstrap 自动下载并校验 SHA-256）作为 PT 侧的执行器，Python 侧只往文件邮箱写命令：

```
%LOCALAPPDATA%\packet-tracer-mcp\bridge\req_<id>.js   -> PT 执行
%LOCALAPPDATA%\packet-tracer-mcp\bridge\res_<id>.txt  <- 结果
%LOCALAPPDATA%\packet-tracer-mcp\bridge\alive.txt     <- 心跳
```

因此 PT 可以最小化、被遮挡、甚至窗口关掉，自动化照跑。

## 一次性 GUI 步骤

PT 8 没有"静默注册脚本模块"的接口，模块只能通过界面登记一次：

`Extensions → Scripting → Configure PT Script Modules → 选中 MCP BUILDER → Settings → On Startup → Start`

登记过一次、设为 On Startup 后，之后每次启动 PT 都会自动轮询，agent 全程无需人介入。

## 已验证 / 未验证

实测（PT 8.0.0.0212）：

- 案例27/28/29 三张拓扑由 JSON 生成并保存；案例28 的 S1–S2 干道自动选交叉线后 `allUp: true`
- `pt_verify_l2()` 读回：`S1:FastEthernet0/13 up=true mode=2(trunk)` / `S2` 同
- `pt_save()` 全程无对话框（含覆盖场景）
- PC（PC-PT）没有 `getIpcTerminalLine`，PC 的 ping 输出**读不到**；需要机器判定时用 `pt_verify_l2()`，
  需要"看得见的 ping"时用 `pt_ping()` 把命令打在 IOS 设备 CLI 上

未验证：

- PT 9.x（API 可能有差异）
- 无人值守下自动登记脚本模块（PT 无此接口）

## 致谢

- [MCP-Packet-Tracer](https://github.com/Mats2208/MCP-Packet-Tracer)（MIT）提供的 PT 侧脚本模块
- [PTBuilder](https://github.com/kimmknight/PTBuilder)（Kim Knight）——PT 脚本引擎 API 的开山实践

MIT License.
