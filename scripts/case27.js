// Case 27: VLAN partitioning (1x 2950T-24 + 2 PC)
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

add("S1", "2950T-24", 1, 300, 150);
add("PC0", "PC-PT", 8, 190, 380);
add("PC1", "PC-PT", 8, 430, 380);
link("S1", "FastEthernet0/1", "PC0", "FastEthernet0");
link("S1", "FastEthernet0/2", "PC1", "FastEthernet0");

// step 1: hosts in 192.168.12.0/24
var p0 = ipc.network().getDevice("PC0").getPort("FastEthernet0");
p0.setIpSubnetMask("192.168.12.1", "255.255.255.0");
var p1 = ipc.network().getDevice("PC1").getPort("FastEthernet0");
p1.setIpSubnetMask("192.168.12.2", "255.255.255.0");
log.push("ip PC0=192.168.12.1 PC1=192.168.12.2");

// step 3: VLANs (CLI, as in the case)
var d = ipc.network().getDevice("S1");
d.enterCommand("!", "global");
["hostname S1", "vlan 2", "name VLAN2", "exit", "vlan 3", "name VLAN3", "exit"].forEach(function (c) {
  try { d.enterCommand(c, ""); } catch (e) { log.push("cli ERR " + c); }
});
log.push("vlan 2/3 created");

// step 4: port membership
function access(port, vlan) {
  var p = ipc.network().getDevice("S1").getPort(port);
  p.setAccessPort(true);
  p.setAccessVlan(vlan);
  log.push("S1 " + port + " -> vlan " + p.getAccessVlan());
}
access("FastEthernet0/1", 2);
access("FastEthernet0/2", 3);
log.push("prompt=" + ipc.network().getDevice("S1").getIpcTerminalLine().getPrompt());

log.push("save=" + ipc.appWindow().fileSaveAs("C:\\pt\\case27_vlan.pkt"));
throw new Error(log.join(" | "));

