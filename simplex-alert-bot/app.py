import asyncio
import contextlib
import hmac
import json
import logging
import os
from pathlib import Path
import signal
import uuid

from aiohttp import ClientSession, ClientTimeout, WSMsgType, web

LOG = logging.getLogger('simplex-alert-bot')
OPTIONS = Path('/data/options.json')
WS_URL = 'http://127.0.0.1:5225'


def load_options():
    options = json.loads(OPTIONS.read_text())
    for key in ('bot_token',):
        if len(options.get(key, '')) < 32:
            raise ValueError(key + ' must contain at least 32 characters')
    if options.get('admin_enabled'):
        if len(options.get('admin_token', '')) < 32:
            raise ValueError('admin_token must contain at least 32 characters')
        if options['admin_token'] == options['bot_token']:
            raise ValueError('Use a separate admin_token')
    name = options.get('bot_name', '')
    if not name or any(c.isspace() for c in name):
        raise ValueError('bot_name must be non-empty and contain no whitespace')
    for target in [options.get('recipient', '')] + options.get('allowed_recipients', []):
        if target and (target[0] not in '@#' or any(c.isspace() for c in target)):
            raise ValueError('Recipients must be @Contact or #Group, without whitespace')
    return options


class Bridge:
    def __init__(self, options):
        self.options = options
        self.lock = asyncio.Lock()

    async def command(self, command):
        async with asyncio.timeout(25):
            async with self.lock:
                async with ClientSession(timeout=ClientTimeout(total=25)) as session:
                    async with session.ws_connect(WS_URL, max_msg_size=4 * 1024 * 1024) as ws:
                        correlation = uuid.uuid4().hex
                        await ws.send_json({'corrId': correlation, 'cmd': command})
                        async for item in ws:
                            if item.type == WSMsgType.TEXT:
                                result = json.loads(item.data)
                                if result.get('corrId') != correlation:
                                    continue
                                response = result.get('resp', {})
                                kind = response.get('type', '')
                                if 'error' in kind.lower():
                                    raise RuntimeError(json.dumps(response))
                                return response
                            if item.type in (WSMsgType.ERROR, WSMsgType.CLOSE, WSMsgType.CLOSED):
                                break
                        raise RuntimeError('SimpleX WebSocket closed without a command response')

    def authorize(self, request, admin=False):
        if admin and not self.options.get('admin_enabled'):
            raise web.HTTPNotFound()
        expected = self.options.get('admin_token' if admin else 'bot_token', '')
        supplied = request.headers.get('X-Admin-Token' if admin else 'X-Bot-Token', '')
        if not expected or not hmac.compare_digest(supplied.encode(), expected.encode()):
            raise web.HTTPUnauthorized(text='Invalid token')

    async def rpc(self, command):
        try:
            return await self.command(command)
        except (TimeoutError, OSError, RuntimeError, ValueError) as exc:
            LOG.warning('SimpleX request failed (%s)', type(exc).__name__)
            raise web.HTTPBadGateway(text='SimpleX request failed: ' + str(exc))

    async def health(self, request):
        try:
            response = await self.command('/u')
            if response.get('type') != 'activeUser':
                raise RuntimeError('No active user')
        except Exception:
            raise web.HTTPServiceUnavailable(text='SimpleX not ready')
        return web.json_response({'ok': True})

    async def read_json(self, request):
        try:
            body = await request.json()
        except (ValueError, UnicodeError):
            raise web.HTTPBadRequest(text='Invalid JSON')
        if not isinstance(body, dict):
            raise web.HTTPBadRequest(text='Expected a JSON object')
        return body

    async def alert(self, request):
        self.authorize(request)
        body = await self.read_json(request)
        target = body.get('recipient', self.options.get('recipient', ''))
        allowed = set(self.options.get('allowed_recipients', []))
        allowed.add(self.options.get('recipient', ''))
        if not isinstance(target, str) or not target or target not in allowed:
            raise web.HTTPBadRequest(text='Recipient is missing or not allowed')
        if 'alerts' in body:
            if not isinstance(body['alerts'], list):
                raise web.HTTPBadRequest(text='alerts must be a list')
            parts = []
            for alert in body['alerts']:
                if not isinstance(alert, dict):
                    raise web.HTTPBadRequest(text='Each alert must be an object')
                labels = alert.get('labels') or {}
                annotations = alert.get('annotations') or {}
                if not isinstance(labels, dict) or not isinstance(annotations, dict):
                    raise web.HTTPBadRequest(text='Invalid alert labels or annotations')
                parts.append('[{}] {}\nHost: {}\n{}\n{}'.format(
                    str(alert.get('status', 'firing')).upper(),
                    labels.get('alertname', 'Alert'), labels.get('instance', labels.get('host', 'unknown')),
                    annotations.get('summary', ''), annotations.get('description', '')))
            text = '\n\n'.join(parts)
        else:
            text = body.get('text')
        if not isinstance(text, str) or not text.strip() or len(text) > 12000:
            raise web.HTTPBadRequest(text='text must contain 1 to 12000 characters')
        response = await self.rpc(target + ' ' + text)
        if response.get('type') != 'newChatItems':
            raise web.HTTPBadGateway(text='Unexpected send response: ' + json.dumps(response))
        return web.json_response({'ok': True, 'status': 'accepted', 'recipient': target})

    async def admin(self, request):
        self.authorize(request, admin=True)
        body = await self.read_json(request)
        command = body.get('command')
        if not isinstance(command, str) or not command.startswith('/') or len(command) > 4096:
            raise web.HTTPBadRequest(text='Expected a slash command, at most 4096 characters')
        return web.json_response(await self.rpc(command))


async def main():
    options = load_options()
    os.umask(0o077)
    Path('/data/simplex').mkdir(parents=True, exist_ok=True)
    stopped = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stopped.set)
    process = await asyncio.create_subprocess_exec(
        '/usr/local/bin/simplex-chat', '-d', '/data/simplex/bot', '-p', '5225',
        '--create-bot-display-name', options['bot_name'], '-y',
        stdin=asyncio.subprocess.DEVNULL)
    bridge = Bridge(options)
    runner = None
    waiter = asyncio.create_task(process.wait())
    stopper = asyncio.create_task(stopped.wait())
    try:
        for _ in range(90):
            if waiter.done():
                raise RuntimeError('SimpleX exited during startup')
            if stopped.is_set():
                return
            try:
                async with asyncio.timeout(2):
                    response = await bridge.command('/u')
                if response.get('type') == 'activeUser':
                    break
            except Exception:
                pass
            await asyncio.sleep(1)
        else:
            raise RuntimeError('SimpleX not ready after startup wait')
        app = web.Application(client_max_size=65536)
        app.router.add_get('/health', bridge.health)
        app.router.add_post('/alert', bridge.alert)
        app.router.add_post('/admin/command', bridge.admin)
        runner = web.AppRunner(app, access_log=None)
        await runner.setup()
        await web.TCPSite(runner, '0.0.0.0', 8080).start()
        LOG.info('Alert API ready on port 8080; setup admin API enabled: %s', options.get('admin_enabled', False))
        done, _ = await asyncio.wait([waiter, stopper], return_when=asyncio.FIRST_COMPLETED)
        if waiter in done and not stopped.is_set():
            raise RuntimeError('SimpleX process exited; terminating app')
    finally:
        if runner:
            await runner.cleanup()
        if process.returncode is None:
            process.terminate()
            try:
                await asyncio.wait_for(asyncio.shield(waiter), 15)
            except TimeoutError:
                process.kill()
                await waiter
        stopper.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await stopper


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
