// Case 28 step 1: place & cable only (no config yet), so switches can finish booting.
var log = [];
ipc.appWindow().fileNew(false);
var lw = ipc.appWindow().getActiveWorkspace().getLogicalWorkspace();
function add(name, model, type, x, y) {
  var o = lw.addDevice(type, model, x, y);
  var d = ipc.network().getDevice(o);
  d.setName(name);
  log.push("+" + name);
  return d;
}
function link(a, ap, b, bp, cable) {
  log.push("link " + a + ":" + ap + "-" + b + ":" + bp + "=" + lw.createLink(a, ap, b, bp, cable || 8100));
}
add("S1", "2950T-24", 1, 260, 140);
add("S2", "2950T-24", 1, 620, 140);
add("PC0", "PC-PT", 8, 150, 400);
add("PC1", "PC-PT", 8, 330, 400);
add("PC2", "PC-PT", 8, 540, 400);
add("PC3", "PC-PT", 8, 720, 400);
link("S1", "FastEthernet0/1", "PC0", "FastEthernet0");
link("S1", "FastEthernet0/2", "PC1", "FastEthernet0");
link("S2", "FastEthernet0/3", "PC2", "FastEthernet0");
link("S2", "FastEthernet0/4", "PC3", "FastEthernet0");
link("S1", "FastEthernet0/13", "S2", "FastEthernet0/13", 8101);
function ip(name, addr, mask) {
  ipc.network().getDevice(name).getPort("FastEthernet0").setIpSubnetMask(addr, mask);
  log.push("ip " + name + "=" + addr);
}
ip("PC0", "192.168.2.1", "255.255.255.0");
ip("PC2", "192.168.2.2", "255.255.255.0");
ip("PC1", "192.168.3.1", "255.255.255.0");
ip("PC3", "192.168.3.2", "255.255.255.0");
throw new Error(log.join(" | "));
