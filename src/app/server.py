import asyncio
import aiohttp
from aiohttp import web
from ddb_utils import put_node_package_ddb, put_node_ddb

print("😂 server")
async def ddb_put_node(request):
    print("ddb_put_node request received")
    # data = await request.json()
    # put_node_package_ddb(data)
    return web.json_response({"status": "success"}, status=200)

async def ddb_put_node_package(request):
    print("ddb_put_node_package request received")
    # data = await request.json()
    # put_node_ddb(data)
    return web.json_response({"status": "success"}, status=200)

async def start_server():
    app = web.Application()
    app.add_routes([
        web.post('/ddb_put_node', ddb_put_node),
        web.post('/ddb_put_node_package', ddb_put_node_package)
    ])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 1234)
    await site.start()

    print("Server started. Press Ctrl+C to stop.")
    await asyncio.Event().wait()

if __name__ == '__main__':
    asyncio.run(start_server())
