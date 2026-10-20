// Case 28 step 2: VLANs + access ports + trunk (run after the switches are up).
var log = [];
function cli(dev, cmds) {
  var d = ipc.network().getDevice(dev);
  d.enterCommand("!", "global");
  for (var i = 0; i < cmds.length; i++) {
    try { d.enterCommand(cmds[i], ""); } catch (e) { log.push("cli " + dev + " ERR " + cmds[i]); }
  }
  log.push("cli " + dev + " -> " + d.getIpcTerminalLine().getPrompt());
}
var vlans = ["vlan 2", "name VLAN2", "exit", "vlan 3", "name VLAN3", "exit"];
cli("S1", vlans);
cli("S2", vlans);

function access(dev, port, vlan) {
  var p = ipc.network().getDevice(dev).getPort(port);
  p.setAccessPort(true);
  p.setAccessVlan(vlan);
  log.push(dev + " " + port + " vlan=" + p.getAccessVlan() + " up=" + p.isPortUp());
}
function trunk(dev, port, nativeVlan) {
  var p = ipc.network().getDevice(dev).getPort(port);
  p.setAdminOpMode(2);
  if (nativeVlan) p.setNativeVlanId(nativeVlan);
  log.push(dev + " " + port + " mode=" + p.getAdminOpMode() + " native=" + p.getNativeVlanId() +
           " up=" + p.isPortUp() + " proto=" + p.isProtocolUp());
}
access("S1", "FastEthernet0/1", 2);
access("S1", "FastEthernet0/2", 3);
access("S2", "FastEthernet0/3", 2);
access("S2", "FastEthernet0/4", 3);
trunk("S1", "FastEthernet0/13", 0);
trunk("S2", "FastEthernet0/13", 2);

var target = "C:\\pt\\case28_trunk.pkt";
log.push("save=" + ipc.appWindow().fileSaveAs(target));
throw new Error(log.join(" | "));
