// Case 29: VTP (3x 2950T-24)
var log = [];
ipc.appWindow().fileNew(false);
var lw = ipc.appWindow().getActiveWorkspace().getLogicalWorkspace();

function add(name, model, type, x, y) {
  var o = lw.addDevice(type, model, x, y);
  var d = ipc.network().getDevice(o);
  d.setName(name);
  try { d.skipBoot(); } catch (e) {}
  log.push("+" + name);
  return d;
}
function link(a, ap, b, bp) {
  log.push("link " + a + ":" + ap + "-" + b + ":" + bp + "=" + lw.createLink(a, ap, b, bp, 8101));
}
function cli(dev, cmds) {
  var d = ipc.network().getDevice(dev);
  d.enterCommand("!", "global");
  for (var i = 0; i < cmds.length; i++) {
    try { d.enterCommand(cmds[i], ""); } catch (e) { log.push("cli " + dev + " ERR " + cmds[i]); }
  }
  log.push("cli " + dev + " ok");
}

add("S1", "2950T-24", 1, 180, 140);
add("S3", "2950T-24", 1, 430, 140);
add("S2", "2950T-24", 1, 680, 140);

link("S1", "FastEthernet0/15", "S3", "FastEthernet0/1");
link("S3", "FastEthernet0/2", "S2", "FastEthernet0/15");

cli("S1", ["hostname S1", "interface f0/15", "switchport mode trunk", "exit",
           "vtp mode server", "vtp domain VTP-TEST", "vtp password cisco",
           "vlan 2", "exit", "vlan 3", "exit"]);
cli("S3", ["hostname S3", "interface range f0/1 - 2", "switchport mode trunk", "exit",
           "vtp mode transparent", "vtp domain VTP-TEST", "vtp password cisco"]);
cli("S2", ["hostname S2", "interface f0/15", "switchport mode trunk", "exit",
           "vtp mode client", "vtp domain VTP-TEST", "vtp password cisco"]);

// trunk as an API attribute too, so the state is deterministic
function trunk(dev, ports) {
  for (var i = 0; i < ports.length; i++) {
    var p = ipc.network().getDevice(dev).getPort(ports[i]);
    p.setAdminOpMode(2);
    log.push(dev + " " + ports[i] + " mode=" + p.getAdminOpMode());
  }
}
trunk("S1", ["FastEthernet0/15"]);
trunk("S3", ["FastEthernet0/1", "FastEthernet0/2"]);
trunk("S2", ["FastEthernet0/15"]);

// try to read CLI output back (show vlan on the client)
try {
  var s2 = ipc.network().getDevice("S2");
  s2.enterCommand("show vlan", "");
  var t = s2.getIpcTerminalLine();
  var keys = [];
  for (var k in t) { keys.push(k); }
  log.push("terminal keys=[" + keys.join(",") + "]");
  try { log.push("txt=" + String(t.getText ? t.getText() : t)); } catch (e) { log.push("txt ERR"); }
} catch (e) { log.push("terminal ERR " + e); }

log.push("save=" + ipc.appWindow().fileSaveAs("C:\\pt\\case29_vtp.pkt"));
throw new Error(log.join(" | "));

