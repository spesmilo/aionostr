import asyncio
import secrets
import time
import sys
import logging
from json import dumps, loads

import aiorpcx

from collections import defaultdict, namedtuple
from websockets import connect, exceptions
from .event import Event



Subscription = namedtuple('Subscription', ['filters','queue'])


class Relay:
    """
    Interact with a relay
    """
    def __init__(self, url, verbose=False, origin:str = '', private_key:str='', connect_timeout: float=1.0, log=None):
        self.log = log or logging.getLogger(__name__)
        self.url = url
        self.ws = None
        self.receive_task = None
        self.subscriptions = defaultdict(lambda: Subscription(filters=[], queue=asyncio.Queue()))
        self.event_adds = asyncio.Queue()
        self.notices = asyncio.Queue()
        self.private_key = private_key
        self.origin = origin or url
        self.connected = False
        self.connect_timeout = connect_timeout

    async def connect(self, taskgroup, retries=2):
        for i in range(retries):
            try:
                self.ws = await asyncio.wait_for(connect(self.url, origin=self.origin), self.connect_timeout)
            except:
                await asyncio.sleep(0.2 * i)
            else:
                break
        else:
            self.log.info(f"Cannot connect to {self.url}")
            return False
        if self.receive_task is None:
            self.receive_task = await taskgroup.spawn(self._receive_messages())
        await asyncio.sleep(0.01)
        self.connected = True
        self.log.info("Connected to %s", self.url)

    async def reconnect(self):
        await self.connect(20)
        for sub_id, sub in self.subscriptions.items():
            self.log.debug("resubscribing to %s", sub.filters)
            await self.send(["REQ", sub_id, *sub.filters])

    async def close(self, taskgroup):
        if self.receive_task:
            self.receive_task.cancel() # fixme: this will cancel taskgroup
        if self.ws:
            await taskgroup.spawn(self.ws.close())
        self.connected = False

    async def _receive_messages(self):
        while True:
            try:
                message = await asyncio.wait_for(self.ws.recv(), 30.0)

                self.log.debug(message)
                message = loads(message)
                if message[0] == 'EVENT':
                    await self.subscriptions[message[1]].queue.put(Event(**message[2]))
                elif message[0] == 'EOSE':
                    await self.subscriptions[message[1]].queue.put(None)
                elif message[0] == 'OK':
                    await self.event_adds.put(message)
                elif message[0] == 'NOTICE':
                    await self.notices.put(message[1])
                elif message[0] == 'AUTH':
                    await self.authenticate(message[1])
                else:
                    sys.stderr.write(message)
            except asyncio.CancelledError:
                return
            except exceptions.ConnectionClosedError:
                await self.reconnect()
            except asyncio.TimeoutError:
                continue
            except:
                import traceback; traceback.print_exc()

    async def send(self, message):
        try:
            await self.ws.send(dumps(message))
        except exceptions.ConnectionClosedError:
            await self.reconnect()
            await self.ws.send(dumps(message))

    async def add_event(self, event, check_response=False):
        if isinstance(event, Event):
            event = event.to_json_object()
        await self.send(["EVENT", event])
        if check_response:
            response = await self.event_adds.get()
            return response[1]

    async def subscribe(self, taskgroup, sub_id: str, *filters, queue=None):
        self.subscriptions[sub_id] = Subscription(filters=filters, queue=queue or asyncio.Queue())
        await taskgroup.spawn(self.send(["REQ", sub_id, *filters]))
        return self.subscriptions[sub_id].queue

    async def unsubscribe(self, sub_id):
        await self.send(["CLOSE", sub_id])
        del self.subscriptions[sub_id]

    async def authenticate(self, challenge:str):
        if not self.private_key:
            import warnings
            warnings.warn("private key required to authenticate")
            return
        from .key import PrivateKey
        if self.private_key.startswith('nsec'):
            from .util import from_nip19
            pk = from_nip19(self.private_key)['object']
        else:
            pk = PrivateKey(bytes.fromhex(self.private_key))
        auth_event = Event(
            kind=22242,
            pubkey=pk.public_key.hex(),
            tags=[
                ['challenge', challenge],
                ['relay', self.url]
            ]
        )
        auth_event.sign(pk.hex())
        await self.send(["AUTH", auth_event.to_json_object()])
        await asyncio.sleep(0.1)
        return True

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, ex_type, ex, tb):
        await self.close()


class Manager:
    """
    Manage a collection of relays
    """
    def __init__(self, relays=None, verbose=False, origin='aionostr', private_key=None, log=None):
        self.log = log or logging.getLogger(__name__)
        self.relays = [Relay(r, origin=origin, private_key=private_key, log=log) for r in (relays or [])]
        self.subscriptions = {}
        self.connected = False
        self._connectlock = asyncio.Lock()
        self.taskgroup = aiorpcx.TaskGroup()

    @property
    def private_key(self):
        return None

    @private_key.setter
    def private_key(self, pk):
        for relay in self.relays:
            relay.private_key = pk

    def add(self, url, **kwargs):
        self.relays.append(Relay(url, **kwargs))

    async def monitor_queues(self, queues, output):
        seen = set()
        async def func(queue):
            while True:
                result = await queue.get()
                if result:
                    eid = result.id_bytes
                    if eid not in seen:
                        await output.put(result)
                        seen.add(eid)
                else:
                    await output.put(None)

        tasks = [func(queue) for queue in queues]
        await asyncio.gather(*tasks)

    async def broadcast(self, func, *args, **kwargs):
        """ returns when all tasks completed. timeout is enforced """
        results = []
        for relay in self.relays:
            coro = asyncio.wait_for(getattr(relay, func)(*args, **kwargs), timeout=5)
            results.append(await self.taskgroup.spawn(coro))

        self.log.debug("Waiting for %s", func)
        return await asyncio.wait(results, return_when=asyncio.ALL_COMPLETED)

    async def connect(self):
        async with self._connectlock:
            if not self.connected:
                await self.broadcast('connect', self.taskgroup)
                self.connected = True
                tried = len(self.relays)
                connected = [relay for relay in self.relays if relay.connected]
                success = len(connected)
                self.relays = connected
                self.log.info("Connected to %d out of %d relays", success, tried)

    async def close(self):
        await self.broadcast('close', self.taskgroup)

    async def add_event(self, event, timeout=5):
        """ waits until one of the tasks succeeds, or raises timeout"""
        queue = asyncio.Queue()
        tasks = []
        async def _add_event(relay):
            try:
                result = await relay.add_event(event, check_response=True)
            except Exception as e:
                self.log.info(f'add_event: failed with {relay.url}')
                return
            await queue.put(result)
        for relay in self.relays:
            await self.taskgroup.spawn(_add_event(relay))
        result = await asyncio.wait_for(queue.get(), timeout=5)
        return result

    async def subscribe(self, sub_id: str, *filters):
        queues = []
        for relay in self.relays:
            queues.append(await relay.subscribe(self.taskgroup, sub_id, *filters))
        queue = asyncio.Queue()
        self.subscriptions[sub_id] = await self.taskgroup.spawn(self.monitor_queues(queues, queue))
        return queue

    async def unsubscribe(self, sub_id):
        await self.broadcast('unsubscribe', sub_id)
        self.subscriptions[sub_id].cancel()
        del self.subscriptions[sub_id]

    async def __aenter__(self):
        await self.taskgroup.__aenter__()
        await self.connect()
        return self

    async def __aexit__(self, ex_type, ex, tb):
        await self.close()
        await self.taskgroup.cancel_remaining()
        await self.taskgroup.__aexit__(ex_type, ex, tb)

    async def get_events(self, *filters, only_stored=True, single_event=False):
        sub_id = secrets.token_hex(4)
        queue = await self.subscribe(sub_id, *filters)
        while True:
            event = await queue.get()
            if event is None:
                if only_stored:
                    break
            else:
                yield event
                if single_event:
                    break
        await self.unsubscribe(sub_id)


