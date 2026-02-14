from kombu.transport import redis

PATIENT_TIMEOUT = 10

class PatientMultiChannelPoller(redis.MultiChannelPoller):
    def _register_BRPOP(self, channel):
        """Enable BRPOP mode for channel."""
        ident = channel, channel.client, 'BRPOP'
        if not self._client_registered(channel, channel.client, 'BRPOP'):
            channel._in_poll = False
            self._register(*ident)
        if not channel._in_poll:  # send BRPOP
            channel._brpop_start(timeout=PATIENT_TIMEOUT)

class Transport(redis.Transport):
    def __init__(self, *args, **kwargs):
        if redis is None:
            raise ImportError('Missing redis library (pip install redis)')
        super().__init__(*args, **kwargs)

        # All channels share the same poller.
        self.cycle = PatientMultiChannelPoller()
