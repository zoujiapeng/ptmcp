import base64, json, os, urllib.request
out = r"C:\Users\zou\八爪鱼下载\pt-mcp\ref\cisco-pt-mcp-src"
os.makedirs(out, exist_ok=True)
files = ["extension/cisco-pt-mcp.pts", "extension/source/userfunctions.js",
         "extension/source/runcode.js", "extension/source/main.js",
         "extension/source/window.js", "extension/source/interface/interface.js"]
for f in files:
    url = "https://api.github.com/repos/muhammadbalawal/cisco-pt-mcp/contents/" + f
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ptmcp", "Accept": "application/vnd.github+json"})
        with urllib.request.urlopen(req, timeout=60) as r:
            j = json.load(r)
        data = base64.b64decode(j["content"])
        name = f.replace("/", "_")
        open(os.path.join(out, name), "wb").write(data)
        print("ok", f, len(data))
    except Exception as e:
        print("FAIL", f, e)
