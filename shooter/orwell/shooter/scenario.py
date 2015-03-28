from .. import yaml2protobuf
import yaml
import zmq


class Socket(object):
    def __init__(self):
        pass

    @property
    def connection_string(self):
        bind = getattr(self, 'bind', False)
        protocol = getattr(self, 'protocol', "tcp")
        if (bind):
            address = getattr(self, 'address', "0.0.0.0")
        else:
            address = getattr(self, 'address', "127.0.0.1")
        return "%s://%s:%i" % (protocol, address, self.port)

    def build(self, context):
        bind = getattr(self, 'bind', False)
        self._zmq_socket = context.socket(self.zmq_method)
        self._zmq_socket.setsockopt(zmq.LINGER, 1)
        if (bind):
            self._zmq_socket.bind(self.connection_string)
        else:
            self._zmq_socket.connect(self.connection_string)

    def __repr__(self):
        return "{%s | %s}" % (self.yaml_tag[1:], self.connection_string)
    

class SocketPull(yaml.YAMLObject, Socket):
    yaml_tag = u'!SocketPull'
    zmq_method = zmq.PULL

    def recv(self, *args, **kwargs):
        return self._zmq_socket.recv(*args, **kwargs)


class SocketPush(yaml.YAMLObject, Socket):
    yaml_tag = u'!SocketPush'
    zmq_method = zmq.PUSH

    def send(self, *args, **kwargs):
        print("SocketPush.send(%s, %s)" % (str(*args), str(**kwargs)))
        self._zmq_socket.send(*args, **kwargs)


class ExchangeMetaClass(type):

    def __new__(cls, name, bases, members):
        #collect up the metaclasses
        metas = [type(base) for base in bases]

        # prune repeated or conflicting entries
        metas = [meta for index, meta in enumerate(metas)
            if not [later for later in metas[index+1:]
                if issubclass(later, meta)]]

        # whip up the actual combined meta class derive off all of these
        meta = type(name, tuple(metas), dict(combined_metas = metas))

        # the member is added here because the constructor does not get
        # called when the objects are constructed from yaml.
        if ("arguments" not in members):
            members["arguments"] = {}

        # make the actual object
        return meta(name, bases, members)

    def __init__(self, name, bases, members):
        for meta in self.combined_metas:
            meta.__init__(self, name, bases, members)


class Exchange(object):
    def __repr__(self):
        return "{%s | message: %s ; arguments: %s}" % (
            self.yaml_tag,
            str(self.message.yaml_tag),
            str(self.arguments))

    #def build(self, zmq_method):
        #pass


class In(yaml.YAMLObject, Exchange):
    __metaclass__ = ExchangeMetaClass
    yaml_tag = u'!In'

    def step(self, in_socket, out_socket):
        print("In.step")
        try:
            zmq_message = in_socket.recv(zmq.NOBLOCK)
        except:
            zmq_message = None
        if (zmq_message):
            print("received zmq message %s" % repr(zmq_message))
            message = yaml2protobuf.Capture.create_from_zmq(zmq_message)
            self.message.compute_differences(message)
        return zmq_message, zmq_message is not None

class Out(yaml.YAMLObject, Exchange):
    __metaclass__ = ExchangeMetaClass
    yaml_tag = u'!Out'
    arguments = {}

    def step(self, in_socket, out_socket):
        print("Out.step")
        out_socket.send(self.message.get_zmq_message(self.arguments))
        return None, True


class Capture(yaml.YAMLObject):
    yaml_tag = u'!Capture'

    def update(self, context):
        self._expanded_value = self.value.format(**context)

    def __eq__(self, other):
        return self._expanded_value == other

    def __repr__(self):
        return "{Capture | %s}" % self.value


class Equal(yaml.YAMLObject):
    yaml_tag = u'!Equal'

    #def build(self, zmq_context):
        #pass

    def step(value, *args):
        """Not finished."""

        return (True, True)

    def __repr__(self):
        return "{Equal | %s}" % str(self.values)


class Thread(yaml.YAMLObject):
    yaml_tag = u'!Thread'

    def build(self, zmq_context):
        self.in_socket.build(zmq_context)
        self.out_socket.build(zmq_context)
        #for step in self.flow:
            #step.build(zmq_context)

    def step(self):
        if (not hasattr(self, "index")):
            self.index = 0
        if (self.index < len(self.flow)):
            result, inc = self.flow[self.index].step(
                self.in_socket, self.out_socket)
            if (inc):
                self.index = (self.index + 1) % len(self.flow)

    def __repr__(self):
        return "{Thread | in_socket = %s ; out_socket = %s ; flow = %s}" % (
            str(self.in_socket),
            str(self.out_socket),
            str(self.flow)
            )


class Scenario(object):
    def __init__(self, yaml_content):
        self._data = yaml.load(yaml_content)
        self._messages = self._data["messages"]
        self._zmq_context = zmq.Context()
        self._threads = self._data["threads"]

    def build(self):
        for thread in self._threads:
            thread.build(self._zmq_context)

    def step(self):
        for thread in self._threads:
            thread.step()
