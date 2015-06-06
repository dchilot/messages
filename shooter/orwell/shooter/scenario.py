from .. import yaml2protobuf
import yaml
import zmq
import collections
import re


class Socket(object):

    """Base class for zmq socket wrappers.

    This should not be instantiated but contains some methods common to
    the derived classes.
    """
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

    """To be used in YAML.

    Wrapper for zmq pull socket.
    """

    yaml_tag = u'!SocketPull'
    zmq_method = zmq.PULL

    def recv(self, *args, **kwargs):
        event = self._zmq_socket.poll(10)
        if (zmq.POLLIN == event):
            return self._zmq_socket.recv(*args, **kwargs)
        else:
            return None


class SocketPush(yaml.YAMLObject, Socket):

    """To be used in YAML.

    Wrapper for zmq push socket.
    """

    yaml_tag = u'!SocketPush'
    zmq_method = zmq.PUSH

    def send(self, data):
        print("SocketPush.send({})".format(repr(data)))
        self._zmq_socket.send(data)


class SocketSubscribe(yaml.YAMLObject, Socket):

    """To be used in YAML.

    Wrapper for zmq sub socket.
    """

    yaml_tag = u'!SocketSubscribe'
    zmq_method = zmq.SUB

    def build(self, zmq_context):
        super(self.__class__, self).build(zmq_context)
        self._zmq_socket.setsockopt(zmq.SUBSCRIBE, "")

    def recv(self, *args, **kwargs):
        event = self._zmq_socket.poll(10)
        print "event =", event
        if (zmq.POLLIN == event):
            return self._zmq_socket.recv(*args, **kwargs)
        else:
            return None


class ExchangeMetaClass(type):

    """Metaclass to combine YAMLObject and base class Exchange.

    adapted from http://stackoverflow.com/a/12144823/3552528
    """

    def __new__(cls, name, bases, members):
        #collect up the metaclasses
        metas = [type(base) for base in bases]

        # prune repeated or conflicting entries
        metas = [meta for index, meta in enumerate(metas)
                 if not [later for later in metas[index+1:]
                         if issubclass(later, meta)]]

        # whip up the actual combined meta class derive off all of these
        meta = type(name, tuple(metas), dict(combined_metas=metas))

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

    """Base class for exchanges which are about sending or receiving messages.

    This should not be instantiated but contains some methods common to
    the derived classes.
    """

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

    """To be used in YAML.

    Class to receive messages in a thread.
    """

    __metaclass__ = ExchangeMetaClass
    yaml_tag = u'!In'

    def step(self):
        print("In.step")
        try:
            zmq_message = self._in_socket.recv()
        except Exception as ex:
            print("Exception in In.step:" + str(ex))
            zmq_message = None
        if (zmq_message):
            print("received zmq message %s" % repr(zmq_message))
            message = yaml2protobuf.Capture.create_from_zmq(zmq_message)
            self.message.compute_differences(message)
            self._repository.add_received_message(self.message)
        return zmq_message, zmq_message is not None


class Out(yaml.YAMLObject, Exchange):

    """To be used in YAML.

    Class to send messages in a thread.
    """

    __metaclass__ = ExchangeMetaClass
    yaml_tag = u'!Out'
    arguments = {}

    def build(self, repository, in_socket, out_socket):
        super(self.__class__, self).build(repository, in_socket, out_socket)

    def step(self):
        print("Out.step")
        print("arguments = " + str(self.arguments))
        expanded_arguments = {key: self._repository.expand(value)
                              for key, value in self.arguments.items()}
        print("expanded arguments = " + str(expanded_arguments))
        self._out_socket.send(
            self.message.encode_zmq_message(expanded_arguments))
        return None, True


class Equal(yaml.YAMLObject):

    """To be used in YAML.

    Class to assert that some given values are equal.
    """

    yaml_tag = u'!Equal'

    def build(self, repository, in_socket, out_socket):
        self._repository = repository
        values_count = len(self.values)
        if (values_count < 2):
            raise Exception(
                "Only {} value(s) found but 2 expected.".format(values_count))

    def step(self, *args):
        print("Equal.step")
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

    """Converts the format of yaml2protobuf.CaptureXXX.captured.

    The only used should be in CaptureRepository to have an easy syntax to
    evaluate user provided expressions to manipulate values captured in
    received messages.
    """

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

    """Deals with values extracted from captures in received messages.

    Warning: there is an unsafe eval performed.
    """

    eval_regexp = re.compile(r'\{[^{].*[^}]\}')

    def __init__(self):
        self._values_from_received_messages = collections.defaultdict(list)

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

    """To be used in YAML.

    Class to describe a succession of steps to be executed in sequence.
    """

    yaml_tag = u'!Thread'

    def build(self, zmq_context):
        self.in_socket.build(zmq_context)
        self.out_socket.build(zmq_context)
        self._repository = CaptureRepository()
        for element in self.flow:
            element.build(self._repository, self.in_socket, self.out_socket)
        if (not hasattr(self, "index")):
            self.index = 0

    def step(self):
        if (self.has_more_steps):
            print("In thread '{name}'".format(name=self.name))
            result, inc = self.flow[self.index].step()
            print("In thread '{name}': "
                  "index = {index} ; result = {result} ; inc = {inc}".format(
                      name=self.name,
                      index=self.index,
                      result=result,
                      inc=inc))
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

    @property
    def has_more_steps(self):
        return (self.index < len(self.flow))

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

    """This is what clients of this module need to use.

    The other classes are only helping build a scenario in YAML which is
    wrapped by this class.
    This is implemented as a context manager so that users do not have to
    remember to call terminate when done to clean zmq objects.
    """

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

    def step_all(self):
        while (self.has_more_steps):
            self.step()

    @property
    def has_more_steps(self):
        return all((thread.has_more_steps for thread in self._threads))

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self.terminate()

    def terminate(self):
        for thread in self._threads:
            thread.terminate()
        self._zmq_context.term()
