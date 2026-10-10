"""ADAPTATION run document CAS; UPSTREAM Redis EVAL atomicity, no HA promise."""
import copy
import threading
from flash.m6_protocol import encode, identity, MAX_BYTES

CAS = """
local old = redis.call('GET', KEYS[1])
if ARGV[1] == '-1' then
  if old then return 0 end
else
  if not old then return -1 end
  if cjson.decode(old).revision ~= tonumber(ARGV[1]) then return 0 end
end
redis.call('SET', KEYS[1], ARGV[2])
return 1
"""


class Unavailable(ConnectionError):
    """No confirmed response; write may have committed. Re-read before retry."""


class MemoryStore:
    """EXTENSION deterministic reference CAS, not Redis transport validation."""
    def __init__(self):
        self.values, self.lock = {}, threading.Lock()
        self.online, self.lose_reply, self.delay = True, False, False

    def read(self, run):
        identity(run)
        if not self.online or self.delay:
            raise Unavailable('simulated disconnect/deadline')
        with self.lock:
            return copy.deepcopy(self.values.get(run))

    def cas(self, run, revision, value):
        if not self.online or self.delay:
            raise Unavailable('simulated disconnect/deadline')
        check_size(value)
        with self.lock:
            old = self.values.get(run)
            current = -1 if old is None else old['revision']
            if current != revision:
                return False
            self.values[run] = copy.deepcopy(value)
        if self.lose_reply:
            self.lose_reply = False
            raise Unavailable('reply lost after commit')
        return True


class RedisStore:
    """Existing redis-py client, finite socket timeouts required by caller.

    No TTL during a run. One standalone Redis, one atomic document key. No
    FLUSH, scan cleanup, background service, cluster/failover or disk ACK claim.
    """
    def __init__(self, client):
        self.client = client
        self.server_id = client.info('server')['run_id']
        options = client.connection_pool.connection_kwargs
        if not options.get('socket_timeout') or not options.get('socket_connect_timeout'):
            raise ValueError('finite Redis socket/connect timeouts required')

    def key(self, run):
        return 'flash:m6a:v1:{' + identity(run) + '}:document'

    def _server(self):
        if self.client.info('server')['run_id'] != self.server_id:
            raise Unavailable('Redis restarted; recovery requires operator inspection/new run')

    def read(self, run):
        import json
        try:
            self._server()
            raw = self.client.get(self.key(run))
            return None if raw is None else json.loads(raw)
        except Unavailable:
            raise
        except Exception as exc:
            raise Unavailable('Redis read unconfirmed: ' + type(exc).__name__) from exc

    def cas(self, run, revision, value):
        check_size(value)
        try:
            self._server()
            result = self.client.eval(CAS, 1, self.key(run), str(revision), encode(value))
            if result == -1:
                raise Unavailable('run document lost; do not reinitialize active run')
            return result == 1
        except Unavailable:
            raise
        except Exception as exc:
            raise Unavailable('Redis write unconfirmed: ' + type(exc).__name__) from exc


def check_size(value):
    if len(encode(value).encode()) > MAX_BYTES:
        raise ValueError('run document capacity exhausted; archive/new run required')


def transaction(store, run, mutate):
    """Pure document mutations only; bounded optimistic contention retries."""
    for _ in range(8):
        doc = store.read(run)
        if doc is None:
            raise Unavailable('missing run registration; recovery blocked')
        revision = doc['revision']
        answer = mutate(doc)
        doc['revision'] = revision + 1
        if store.cas(run, revision, doc):
            return answer
    raise Unavailable('CAS contention exceeded bounded retries')
