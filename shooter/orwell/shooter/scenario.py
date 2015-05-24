from .. import yaml2protobuf
import yaml
import zmq
import collections
import re


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
        self.bind = bind
        self._zmq_socket = context.socket(self.zmq_method)
        self._zmq_socket.setsockopt(zmq.LINGER, 1)
        if (bind):
            self._zmq_socket.bind(self.connection_string)
        else:
            self._zmq_socket.connect(self.connection_string)

    def __repr__(self):
        return "{%s | %s}" % (self.yaml_tag[1:], self.connection_string)

    def terminate(self):
        if (self.bind):
            self._zmq_socket.unbind(self.connection_string)
        else:
            self._zmq_socket.disconnect(self.connection_string)
    

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

    def set_context(self, context):
        pass

    #def build(self, zmq_method):
        #pass


class In(yaml.YAMLObject, Exchange):
    __metaclass__ = ExchangeMetaClass
    yaml_tag = u'!In'

    def set_context(self, context):
        self._context = context

    # TODO: move the two sockets in build / set_context
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
            self._context.add_received_message(self.message)
        return zmq_message, zmq_message is not None


class Out(yaml.YAMLObject, Exchange):
    __metaclass__ = ExchangeMetaClass
    yaml_tag = u'!Out'
    arguments = {}

    # TODO: move the two sockets in build / set_context
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
    eval_regexp = re.compile(r'\{[^{].*[^}]\}')

    #def build(self, zmq_context):
        #pass

    def step(self, *args):
        """Not finished."""

        print("Equal::step")
        print(self)
        formatted_values = []
        reference = None
        all_equal = True
        for value in self.values:
            if (Equal.eval_regexp.match(value)):
                # TODO: find a way not to access the private member
                print(self._context._received_messages)
                value = str(
                    eval(value[1:-1], self._context._received_messages))
            if (reference is None):
                reference = value
            else:
                if (reference != value):
                    print("Values differ:", reference, value)
                    all_equal = False
                    break
        return (all_equal, True)

    def __repr__(self):
        return "{Equal | %s}" % str(self.values)

    def set_context(self, context):
        self._context = context


class CaptureConverter(object):
    def __init__(self, capture_list):
        self._values = {}
        print("capture_list")
        print(capture_list)
        for dico in capture_list:
            for key, value in dico.items():
                if (key in self._values):
                    raise Exception("Duplicate key: '" + key + "'")
                self._values[key] = value

    def __getattribute__(self, attribute):
        values = object.__getattribute__(self, "_values")
        if (attribute in values):
            return values[attribute]
        else:
            return object.__getattribute__(self, attribute)


class Thread(yaml.YAMLObject):
    yaml_tag = u'!Thread'

    def build(self, zmq_context):
        self.in_socket.build(zmq_context)
        self.out_socket.build(zmq_context)
        # not really the full messages but the values extracted
        self._received_messages = collections.defaultdict(list)
        for element in self.flow:
            element.set_context(self)

    def step(self):
        if (not hasattr(self, "index")):
            self.index = 0
        if (self.index < len(self.flow)):
            result, inc = self.flow[self.index].step(
                self.in_socket, self.out_socket)
            if (result is not None and not result):
                print("Failure at index " + str(self.index))
                raise Exception("Failure at index " + str(self.index))
            if (inc):
                self.index = (self.index + 1) % len(self.flow)

    def terminate(self):
        self.in_socket.terminate()
        self.out_socket.terminate()

    def __repr__(self):
        return "{Thread | in_socket = %s ; out_socket = %s ; flow = %s}" % (
            str(self.in_socket),
            str(self.out_socket),
            str(self.flow)
            )

    def add_received_message(self, message):
        # message is of type CaptureXXX
        capture_converter = CaptureConverter(message.captured)
        if (hasattr(capture_converter, "id")):
            print("capture_converter.id")
            print(capture_converter.id)
        else:
            print("No id in " + str(message))
        self._received_messages[message.message_type].append(
            capture_converter)


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

    def terminate(self):
        # TODO: clean
        # it is ugly to have to call this to close the sockets
        for thread in self._threads:
            thread.terminate()
