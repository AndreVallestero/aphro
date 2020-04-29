from asyncio import Event, create_task, Task, gather, Queue, get_event_loop, run, sleep
from concurrent.futures._base import CancelledError
from aiohttp import ClientSession
from proxybroker import Broker
from time import time

class Aphro:
    def __init__(self, pool_size = 8, valid_codes = [[200, 300]], timeout = 900,
                 proxies = [], min_proxies = 8, max_proxies = 12,
                 proxy_sample_th = 8, proxy_rate_th = .5):
        self.pool_size = pool_size
        self.valid_codes = valid_codes
        self.timeout = timeout

        self.proxies = proxies # ['proxystring', total_uses, sucesses]
        self.min_proxies = min_proxies
        self.max_proxies = max_proxies
        self.proxy_sample_threshold = proxy_sample_th
        self.proxy_rate_threshold = proxy_rate_th

        self._result = None
        self._args = []
        self._kwargs = {}
        self._tasks = []
        self._event = None
        self._timeout_time = None

        self._proxy_counter = 0

    def __call__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self._timeout_time = time() + self.timeout

        self.update_proxies()
        run(self.initial_spawn(), debug=True)
        return self._result

    # Rewrite class to be defined inside a loop so event and session only need to be instantiated once
    async def initial_spawn(self):
        self._session = ClientSession()
        self._event = Event()

        for _ in range(self.pool_size):
            self.spawn()

        await self._event.wait()
    
    def spawn(self):
        if time() > self._timeout_time:
            raise TimeoutError

        print('Spawning task...')
        task = create_task(self.fetch(self.get_proxy()[0]))
        task.add_done_callback(self.callback)
        self._tasks.append(task)

    def get_proxy(self):
        proxy = self.proxies[self._proxy_counter]
        self._proxy_counter = (self._proxy_counter + 1) % len(self.proxies)
        return proxy

    def update_proxies(self):
        self.proxies = [proxy for proxy in self.proxies if 
                    proxy[1] > self.proxy_sample_threshold and 
                    proxy[2] / proxy[1] < self.proxy_rate_threshold]

        len_proxies = len(self.proxies)
        if len_proxies < self.min_proxies:
            self.gen_proxies(self.max_proxies - len_proxies)
                
    def gen_proxies(self, num_proxies):
        print(f'Attempting to generate {num_proxies} proxies')
        proxy_queue = Queue()
        broker = Broker(proxy_queue)
        tasks = gather(broker.find(types=['HTTP'], limit=num_proxies),
            self.add_proxies(proxy_queue))

        loop = get_event_loop()
        loop.set_debug(True)
        loop.run_until_complete(tasks)

    async def add_proxies(self, proxy_queue):
        while True:
            proxy = await proxy_queue.get()
            if proxy is None: break
            self.proxies.append([f'{proxy.host}:{proxy.port}', 0, 0])
            print(f'Generated proxy {proxy.host}:{proxy.port}')

    async def fetch(self, proxy):
        try:
            print(f'Using proxy {proxy}')
            self.kwargs['proxy'] = f'http://{proxy}'
            async with self._session.request(*self.args, **self.kwargs) as response:
                return response
        except CancelledError as _:
            pass
        except RuntimeError as e:
            print(f'Runtime error (session was probably instantiated outside of an event loop): {e}')
        except:
            print("Unexpected error:", sys.exc_info()[0])
            return 0

    def callback(self, task: Task):
        if self._event.is_set():
            return

        # Check if the code is valid
        try:
            response = task.result()
            code = response.status
            for valid_range in self.valid_codes:
                if ((len(valid_range) == 2 and
                    valid_range[0] <= code <= valid_range[1]) or
                    valid_range[0] == code):
                    break
            # Spawn new task if code is invalid
            else:
                self.spawn()
                return

        # Spawn new task if TimeoutError was recieved
        except TimeoutError as _:
            self.spawn()
            return

        for _task in self._tasks:
            _task.cancel()
        self._result = response.read()
        self._event.set()

def main():
    aphro = Aphro()
    result = aphro('GET', 'http://httpbin.org/get')
    print(result)

main()
