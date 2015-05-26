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

    def build(self, zmq_context):
        bind = getattr(self, 'bind', False)
        self.bind = bind
        self._zmq_socket = zmq_context.socket(self.zmq_method)
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
        self._zmq_socket.close()
    

class SocketPull(yaml.YAMLObject, Socket):
    yaml_tag = u'!SocketPull'
    zmq_method = zmq.PULL

    def recv(self, *args, **kwargs):
        return self._zmq_socket.recv(*args, **kwargs)


class SocketPush(yaml.YAMLObject, Socket):
    yaml_tag = u'!SocketPush'
    zmq_method = zmq.PUSH

    def send(self, data):
        print("SocketPush.send({})".format(repr(data)))
        self._zmq_socket.send(data)


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

    def build(self, repository, in_socket, out_socket):
        self._in_socket = in_socket
        self._out_socket = out_socket
        self._repository = repository


class In(yaml.YAMLObject, Exchange):
    __metaclass__ = ExchangeMetaClass
    yaml_tag = u'!In'

    def step(self):
        print("In.step")
        try:
            zmq_message = self._in_socket.recv(zmq.NOBLOCK)
        except:
            zmq_message = None
        if (zmq_message):
            print("received zmq message %s" % repr(zmq_message))
            message = yaml2protobuf.Capture.create_from_zmq(zmq_message)
            self.message.compute_differences(message)
            self._repository.add_received_message(self.message)
        return zmq_message, zmq_message is not None


class Out(yaml.YAMLObject, Exchange):
    __metaclass__ = ExchangeMetaClass
    yaml_tag = u'!Out'
    arguments = {}

    def build(self, repository, in_socket, out_socket):
        super(self.__class__, self).build(repository, in_socket, out_socket)

    def step(self):
        print("Out.step")
        self._out_socket.send(self.message.get_zmq_message(self.arguments))
        return None, True


class Equal(yaml.YAMLObject):
    yaml_tag = u'!Equal'

    def build(self, repository, in_socket, out_socket):
        self._repository = repository
        values_count = len(self.values)
        if (values_count < 2):
            raise Exception(
                "Only {} value(s) found but 2 expected.".format(values_count))

    def step(self, *args):
        print("Equal.step")
        formatted_values = []
        reference = None
        all_equal = True
        for value in self.values:
            value = self._repository.expand(value)
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


class CaptureRepository(object):
    eval_regexp = re.compile(r'\{[^{].*[^}]\}')

    def __init__(self):
        self._values_from_received_messages =  collections.defaultdict(list)

    def add_received_message(self, message):
        # message is of type CaptureXXX
        capture_converter = CaptureConverter(message.captured)
        self._values_from_received_messages[message.message_type].append(
            capture_converter)

    def expand(self, string):
        if (CaptureRepository.eval_regexp.match(string)):
            string_without_brackets = string[1:-1]
            value = str(eval(
                string_without_brackets,
                self._values_from_received_messages))
        else:
            value = string
        return value


class Thread(yaml.YAMLObject):
    yaml_tag = u'!Thread'

    def build(self, zmq_context):
        self.in_socket.build(zmq_context)
        self.out_socket.build(zmq_context)
        self._repository = CaptureRepository()
        for element in self.flow:
            element.build(self._repository, self.in_socket, self.out_socket)

    def step(self):
        if (not hasattr(self, "index")):
            self.index = 0
        if (self.index < len(self.flow)):
            print("In thread '{name}'".format(name=self.name))
            result, inc = self.flow[self.index].step()
            print("In thread '{name}': "
                    "index = {index} ; result = {result} ; inc = {inc}".format(
                name=self.name, index=self.index, result=result, inc=inc))
            if (result is not None and not result):
                error_message = "Failure at index {} in thread '{}'.".format(
                    self.index, self.name)
                raise Exception(error_message)
            if (inc):
                self.index = (self.index + 1)
                if (self.loop):
                    self.index %= len(self.flow)
        else:
            print("Skipped thread '{name}'".format(name=self.name))

    def terminate(self):
        self.in_socket.terminate()
        self.out_socket.terminate()

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

    def terminate(self):
        # TODO: clean
        # it is ugly to have to call this to close the sockets
        for thread in self._threads:
            thread.terminate()
        self._zmq_context.term()
