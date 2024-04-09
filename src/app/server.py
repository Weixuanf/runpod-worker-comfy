import asyncio
from aiohttp import web
from ddb_utils import put_node_package_ddb, put_node_ddb

async def putNode(request):
    data = await request.json()
    put_node_ddb(data)
    return web.json_response({"status": "success"}, status=200)

async def putNodePackage(request):
    data = await request.json()
    put_node_package_ddb(data)
    return web.json_response({"status": "success"}, status=200)

async def start_server():
    app = web.Application()
    app.add_routes([
        web.post('/putNode', putNode),
        web.post('/putNodePackage', putNodePackage)
    ])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 1234)
    await site.start()

    print("Server started at http://localhost:1234")
    await asyncio.Event().wait()

if __name__ == '__main__':
    asyncio.run(start_server())
