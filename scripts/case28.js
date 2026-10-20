// Case 28: Trunk configuration (2x 2950T-24 + 4 PC)
var log = [];
ipc.appWindow().fileNew(false);
var lw = ipc.appWindow().getActiveWorkspace().getLogicalWorkspace();

function add(name, model, type, x, y) {
  var o = lw.addDevice(type, model, x, y);
  var d = ipc.network().getDevice(o);
  d.setName(name);
  try { if (type <= 1 || type === 16) d.skipBoot(); } catch (e) {}
  log.push("+" + name);
  return d;
}
function link(a, ap, b, bp) {
  log.push("link " + a + ":" + ap + "-" + b + ":" + bp + "=" + lw.createLink(a, ap, b, bp, 8100));
}
function ip(name, addr, mask) {
  var p = ipc.network().getDevice(name).getPort("FastEthernet0");
  p.setIpSubnetMask(addr, mask);
  log.push("ip " + name + "=" + addr);
}

var S1 = add("S1", "2950T-24", 1, 260, 140);
var S2 = add("S2", "2950T-24", 1, 620, 140);
add("PC0", "PC-PT", 8, 150, 400);
add("PC1", "PC-PT", 8, 330, 400);
add("PC2", "PC-PT", 8, 540, 400);
add("PC3", "PC-PT", 8, 720, 400);

link("S1", "FastEthernet0/1", "PC0", "FastEthernet0");
link("S1", "FastEthernet0/2", "PC1", "FastEthernet0");
link("S2", "FastEthernet0/3", "PC2", "FastEthernet0");
link("S2", "FastEthernet0/4", "PC3", "FastEthernet0");
link("S1", "FastEthernet0/13", "S2", "FastEthernet0/13");

ip("PC0", "192.168.2.1", "255.255.255.0");
ip("PC2", "192.168.2.2", "255.255.255.0");
ip("PC1", "192.168.3.1", "255.255.255.0");
ip("PC3", "192.168.3.2", "255.255.255.0");

// VLAN database + names, exactly as in the case (CLI)
function cli(dev, cmds) {
  var d = ipc.network().getDevice(dev);
  d.enterCommand("!", "global");
  for (var i = 0; i < cmds.length; i++) {
    try { d.enterCommand(cmds[i], ""); } catch (e) { log.push("cli " + dev + " ERR " + cmds[i]); }
  }
}
var vlans = ["vlan 2", "name VLAN2", "exit", "vlan 3", "name VLAN3", "exit"];
cli("S1", vlans);
cli("S2", vlans);

// port membership + trunk, set through the port API (deterministic)
function access(dev, port, vlan) {
  var p = ipc.network().getDevice(dev).getPort(port);
  p.setAccessPort(true);
  p.setAccessVlan(vlan);
  log.push(dev + " " + port + " -> vlan " + p.getAccessVlan());
}
function trunk(dev, port, nativeVlan) {
  var p = ipc.network().getDevice(dev).getPort(port);
  p.setAdminOpMode(2);
  if (nativeVlan) { p.setNativeVlanId(nativeVlan); }
  log.push(dev + " " + port + " trunk mode=" + p.getAdminOpMode() + " native=" + p.getNativeVlanId() + " access?=" + p.isAccessPort());
}
access("S1", "FastEthernet0/1", 2);
access("S1", "FastEthernet0/2", 3);
access("S2", "FastEthernet0/3", 2);
access("S2", "FastEthernet0/4", 3);
trunk("S1", "FastEthernet0/13", 0);
trunk("S2", "FastEthernet0/13", 2);

log.push("save=" + ipc.appWindow().fileSaveAs("C:\\pt\\case28_trunk.pkt"));
throw new Error(log.join(" | "));
