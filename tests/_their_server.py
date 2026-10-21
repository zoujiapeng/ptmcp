import asyncio, json, sys, time

async def main():
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    p = StdioServerParameters(command=sys.executable, args=["-m", "mcp_server.server"])
    out = {}
    t0 = time.time()
    try:
        async with stdio_client(p) as (r, w):
            async with ClientSession(r, w) as s:
                await s.initialize()
                tools = await s.list_tools()
                out["tools"] = len(tools.tools)
                t1 = time.time()
                res = await s.call_tool("getNetwork", {})
                text = " ".join(getattr(b, "text", "") for b in res.content)
                out["getNetwork"] = {"ok": not res.isError, "s": round(time.time()-t1,1), "head": text[:220]}
    except Exception as e:
        out["error"] = str(e)[:200]
    out["total_s"] = round(time.time()-t0, 1)
    print(json.dumps(out, ensure_ascii=False, indent=2))

asyncio.run(main())
