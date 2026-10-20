// PT 8.0 topology builder - runs inside Packet Tracer's Script Engine.
// API discovered from PT's own IPC layer + PTBuilder source.
var log = [];

function findType(model) {
    var map = {
        "2911": 0, "2901": 0, "1941": 0, "1841": 0, "2811": 0, "ISR4321": 0,
        "2960-24TT": 1, "2950-24": 1, "3560-24PS": 16, "3650-24PS": 16,
        "PC-PT": 8, "Server-PT": 9, "Laptop-PT": 17, "Printer-PT": 10
    };
    return map[model];
}

function makeDevice(name, model, x, y) {
    var lw = ipc.appWindow().getActiveWorkspace().getLogicalWorkspace();
    var t = findType(model);
    if (t === undefined) { log.push("no type for " + model); return null; }
    var orig = lw.addDevice(t, model, x, y);
    if (!orig) { log.push("addDevice failed: " + name + " (" + model + ", type " + t + ")"); return null; }
    var dev = ipc.network().getDevice(orig);
    if (!dev) { log.push("getDevice failed: " + orig); return null; }
    dev.setName(name);
    try { if (t <= 1 || t === 16) { dev.skipBoot(); } } catch (e) { log.push("skipBoot " + name + ": " + e); }
    log.push("added " + name + " (" + model + ") as " + orig);
    return dev;
}

function link(a, ap, b, bp, typeInt) {
    var lw = ipc.appWindow().getActiveWorkspace().getLogicalWorkspace();
    var ok = lw.createLink(a, ap, b, bp, typeInt);
    log.push("link " + a + ":" + ap + " <-> " + b + ":" + bp + " => " + ok);
    return ok;
}

function portNames(name) {
    var dev = ipc.network().getDevice(name);
    try { return dev.getPorts().join(","); } catch (e) { return "ERR:" + e; }
}

// ---- build ----
makeDevice("R1",  "2911",      300, 140);
makeDevice("SW1", "2960-24TT", 300, 300);
makeDevice("PC1", "PC-PT",     170, 450);
makeDevice("PC2", "PC-PT",     430, 450);

log.push("R1 ports: "  + portNames("R1"));
log.push("SW1 ports: " + portNames("SW1"));
log.push("PC1 ports: " + portNames("PC1"));

link("R1", "GigabitEthernet0/0", "SW1", "GigabitEthernet0/1", 8100);
link("SW1", "FastEthernet0/1", "PC1", "FastEthernet0", 8100);
link("SW1", "FastEthernet0/2", "PC2", "FastEthernet0", 8100);

var ws = ipc.appWindow().getActiveWorkspace().getLogicalWorkspace();
log.push("devices=" + ipc.network().getDeviceCount() + " links=" + ipc.network().getLinkCount());
log.push("canvasItems=" + ws.getCanvasItemIds().length);

throw new Error(log.join(" || "));
