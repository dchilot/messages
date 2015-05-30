import re
import sys
import inspect

import yaml
from pbjson.pbjson import pb2dict
from pbjson.pbjson import dict2pb

import orwell.messages.controller_pb2
import orwell.messages.robot_pb2
import orwell.messages.server_game_pb2
import orwell.messages.server_web_pb2

import google.protobuf.descriptor as pb_descriptor


# adapted from http://stackoverflow.com/a/12144823/3552528
class CustomMetaClass(type):

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
        members['message'] = {}

        # make the actual object
        return meta(name, bases, members)

    def __init__(self, name, bases, members):
        for meta in self.combined_metas:
            meta.__init__(self, name, bases, members)


class Base(object):
    CAPTURE_PATTERN = re.compile('{[^{].*[^}]}')

    def __init__(self, payload, destination=None):
        self._message = self.PROTOBUF_CLASS()
        self._message.ParseFromString(payload)
        self.message = pb2dict(self._message)
        self.destination = destination

    def load(self):
        self._message = dict2pb(self.PROTOBUF_CLASS, self.message)

    @property
    def protobuf_message(self):
        if (not hasattr(self, '_message')):
            self.load()
        return self._message

    def __getattribute__(self, attribute):
        message = object.__getattribute__(self, "message")
        if ("message" == attribute):
            return message
        else:
            if (attribute in message):
                # this seems to never be visited but is kept just in case
                return message[attribute]
            else:
                return object.__getattribute__(self, attribute)

    def __repr__(self):
        return "%s(%s)" % (
            self.__class__.__name__,
            str(self.message),
        )

    @property
    def key_map(self):
        if (not hasattr(self, '_key_map')):
            path = []
            path_stack = [""]
            pb_stack = [self.protobuf_message]
            self._key_map = {}
            first = True
            while (pb_stack):
                message = pb_stack.pop()
                if (path_stack):
                    path.append(path_stack.pop())
                for field in message.ListFields():
                    descriptor, value = field
                    path.append(descriptor.name)
                    if (descriptor.type in
                            (pb_descriptor.FieldDescriptor.TYPE_GROUP,
                             pb_descriptor.FieldDescriptor.TYPE_MESSAGE)):
                        # nested message
                        pb_stack.append(value)
                        path_stack.append(path.pop())
                    else:
                        key = "/".join(path)
                        self._key_map[key] = value
                        path.pop()
                if (not first):
                    path.pop()
                else:
                    first = False
        return self._key_map


class Capture(object):
    def __new__(cls, *args, **kwargs):
        instance = object.__new__(cls, *args, **kwargs)
        if (not hasattr(instance, 'arguments')):
            setattr(instance, 'arguments', {})
        setattr(instance, 'captured', [])
        setattr(instance, '_pb_message', None)
        # !CaptureMessage -> !Message
        setattr(
            instance,
            'captured_yaml_tag',
            instance.yaml_tag.replace('!Capture', '!'))
        return instance

    @staticmethod
    def create_from_zmq(zmq_message):
        destination, message_type, payload = zmq_message.split(' ', 3)
        found = False
        for module in (
                orwell.messages.controller_pb2,
                orwell.messages.robot_pb2,
                orwell.messages.server_game_pb2,
                orwell.messages.server_web_pb2):
            if (hasattr(module, message_type)):
                pb_klass = getattr(module, message_type)
                found = True
                break
        if (not found):
            raise Exception("Invalid message type: " + message_type)
        pb_message = pb_klass()
        pb_message.ParseFromString(payload)
        klass = getattr(sys.modules[__name__], "Capture" + message_type)
        capture = klass()
        capture._pb_message = pb_message
        capture.destination = destination
        capture.message = pb2dict(pb_message)
        return capture

    @property
    def protobuf_message(self):
        if (self._pb_message is None):
            self._pb_message = self.fill(self.arguments)
            #self._pb_message = dict2pb(self.PROTOBUF_CLASS, self.message)
        return self._pb_message

    @property
    def key_map(self):
        if (not hasattr(self, '_key_map')):
            path = []
            path_stack = [""]
            dico_stack = [self.message]
            self._key_map = {}
            first  = True
            while (dico_stack):
                dico = dico_stack.pop()
                if (path_stack):
                    path.append(path_stack.pop())
                for dico_key, value in dico.items():
                    path.append(dico_key)
                    if (isinstance(value, dict)):
                        # nested message
                        dico_stack.append(value)
                        path_stack.append(path.pop())
                    else:
                        key = "/".join(path)
                        self._key_map[key] = value
                        path.pop()
                if (not first):
                    path.pop()
                else:
                    first = False
        return self._key_map

    def encode_zmq_message(self, dico):
        if (('{' == self.destination[0]) and ('}' == self.destination[-1])):
            destination = self.destination.format(**dico)
        else:
            destination = self.destination
        return " ".join((
            destination,
            self.PROTOBUF_CLASS.DESCRIPTOR.name,
            self.fill(dico).SerializeToString()))

    def __getitem__(self, index):
        return self.captured[index]

    def __getattribute__(self, attribute):
        if (hasattr(self, "message")):
            message = object.__getattribute__(self, "message")
            if ("message" == attribute):
                return message
            else:
                if (attribute in message):
                    return message[attribute]
                else:
                    return object.__getattribute__(self, attribute)
        else:
            return object.__getattribute__(self, attribute)

    def compute_differences(self, other):
        differences = []
        captured = {}
        if (self.captured_yaml_tag != other.yaml_tag):
            differences.append(
                ("@name", self.captured_yaml_tag, other.yaml_tag))
        if (self.destination != other.destination):
            differences.append(
                ("@destination", self.destination, other.destination))
        for key, reference_value in self.key_map.items():
            other_value = other.key_map[key]
            if (reference_value != other_value):
                if ((isinstance(reference_value, str)) and
                        (Base.CAPTURE_PATTERN.match(reference_value))):
                    capture_name = reference_value[1:-1]
                    captured[capture_name] = other_value
                else:
                    differences.append((key, reference_value, other_value))
        self.captured.append(captured)
        print("self")
        print(self)
        print("self.captured")
        print(self.captured)
        return differences

    def fill(self, dico):
        expanded_dico = {}
        sys.stderr.write("++ self.message %s\n" % (self.message))
        stack = [(self.message, expanded_dico, self.PROTOBUF_CLASS.DESCRIPTOR)]
        while (stack):
            current_dico, current_expanded_dico, current_descriptor = \
                stack.pop()
            for key, value in current_dico.items():
                sys.stderr.write("-- key={0};value={1} ; {2}\n".format(
                    key, value, current_descriptor))
                if (isinstance(current_descriptor, pb_descriptor.Descriptor)):
                    descriptor = current_descriptor.fields_by_name[key]
                else:
                    descriptor = current_descriptor\
                        .message_type.fields_by_name[key]
                if (isinstance(value, dict)):
                    current_expanded_dico[key] = {}
                    stack.append(
                        (value, current_expanded_dico[key], descriptor))
                else:
                    #for field in current_descriptor.fields:
                        #if (field.name == key):
                            #descriptor = field
                            #break
                    if (isinstance(value, str)):
                        value = value.format(**dico)
                    if (descriptor.type in
                            (pb_descriptor.FieldDescriptor.TYPE_DOUBLE,
                             pb_descriptor.FieldDescriptor.TYPE_FLOAT)):
                        value = float(value)
                    elif (descriptor.type in
                            (pb_descriptor.FieldDescriptor.TYPE_INT32,
                             pb_descriptor.FieldDescriptor.TYPE_SINT32,
                             pb_descriptor.FieldDescriptor.TYPE_UINT32,
                             pb_descriptor.FieldDescriptor.TYPE_FIXED32,
                             pb_descriptor.FieldDescriptor.TYPE_SFIXED32,
                             pb_descriptor.FieldDescriptor.TYPE_INT64,
                             pb_descriptor.FieldDescriptor.TYPE_SINT64,
                             pb_descriptor.FieldDescriptor.TYPE_UINT64,
                             pb_descriptor.FieldDescriptor.TYPE_FIXED64,
                             pb_descriptor.FieldDescriptor.TYPE_SFIXED64,
                             pb_descriptor.FieldDescriptor.TYPE_ENUM)):
                        value = int(value)
                    elif (pb_descriptor.FieldDescriptor.TYPE_BOOL
                            == descriptor.type):
                        value = bool(value)
                    current_expanded_dico[key] = value
        return dict2pb(self.PROTOBUF_CLASS, expanded_dico)


def get_classes_from_module(module):
    """ Extract module and name of classes.

    Simple version that does not deal with classes nested in other classes.
    """
    classes_and_modules = []
    class_descriptions = inspect.getmembers(module, inspect.isclass)
    for class_description in class_descriptions:
        name, klass = class_description
        module = klass.__module__
        classes_and_modules.append((name, module))
    return classes_and_modules


def generate():
    """Used to generate code with cog."""
    import orwell.messages.controller_pb2 as pb_controller
    import orwell.messages.robot_pb2 as pb_robot
    import orwell.messages.server_game_pb2 as pb_server_game
    import orwell.messages.server_web_pb2 as pb_server_web

    TEMPLATE = """
class {name}(yaml.YAMLObject, Base):
    __metaclass__ = CustomMetaClass
    PROTOBUF_CLASS = {module}.{name}
    yaml_tag = u'!{name}'


class Capture{name}(yaml.YAMLObject, Capture):
    PROTOBUF_CLASS = {module}.{name}
    yaml_tag = u'!Capture{name}'
    message_type = '{name}'

"""
    output = ""

    output += "\n"
    array = get_classes_from_module(pb_controller)
    array += get_classes_from_module(pb_robot)
    array += get_classes_from_module(pb_server_game)
    array += get_classes_from_module(pb_server_web)
    for class_name, module_name in array:
        output += TEMPLATE.format(name=class_name, module=module_name)
    return output


# use to generator the code with cog
COG_GENERATOR = """ [[[cog
import os
import sys
import inspect
full_path = os.path.abspath(inspect.getfile(inspect.currentframe()))
plus_index = full_path.rfind('+')
real_path = full_path[:plus_index]
print('exec(%s)' % real_path)
exec(open(real_path, 'r'))
import cog
cog.outl(generate())
# ]]] """


class Fire(yaml.YAMLObject, Base):
    __metaclass__ = CustomMetaClass
    PROTOBUF_CLASS = orwell.messages.controller_pb2.Fire
    yaml_tag = u'!Fire'


class CaptureFire(yaml.YAMLObject, Capture):
    PROTOBUF_CLASS = orwell.messages.controller_pb2.Fire
    yaml_tag = u'!CaptureFire'
    message_type = 'Fire'


class Hello(yaml.YAMLObject, Base):
    __metaclass__ = CustomMetaClass
    PROTOBUF_CLASS = orwell.messages.controller_pb2.Hello
    yaml_tag = u'!Hello'


class CaptureHello(yaml.YAMLObject, Capture):
    PROTOBUF_CLASS = orwell.messages.controller_pb2.Hello
    yaml_tag = u'!CaptureHello'
    message_type = 'Hello'


class Input(yaml.YAMLObject, Base):
    __metaclass__ = CustomMetaClass
    PROTOBUF_CLASS = orwell.messages.controller_pb2.Input
    yaml_tag = u'!Input'


class CaptureInput(yaml.YAMLObject, Capture):
    PROTOBUF_CLASS = orwell.messages.controller_pb2.Input
    yaml_tag = u'!CaptureInput'
    message_type = 'Input'


class Move(yaml.YAMLObject, Base):
    __metaclass__ = CustomMetaClass
    PROTOBUF_CLASS = orwell.messages.controller_pb2.Move
    yaml_tag = u'!Move'


class CaptureMove(yaml.YAMLObject, Capture):
    PROTOBUF_CLASS = orwell.messages.controller_pb2.Move
    yaml_tag = u'!CaptureMove'
    message_type = 'Move'


class Colour(yaml.YAMLObject, Base):
    __metaclass__ = CustomMetaClass
    PROTOBUF_CLASS = orwell.messages.robot_pb2.Colour
    yaml_tag = u'!Colour'


class CaptureColour(yaml.YAMLObject, Capture):
    PROTOBUF_CLASS = orwell.messages.robot_pb2.Colour
    yaml_tag = u'!CaptureColour'
    message_type = 'Colour'


class Register(yaml.YAMLObject, Base):
    __metaclass__ = CustomMetaClass
    PROTOBUF_CLASS = orwell.messages.robot_pb2.Register
    yaml_tag = u'!Register'


class CaptureRegister(yaml.YAMLObject, Capture):
    PROTOBUF_CLASS = orwell.messages.robot_pb2.Register
    yaml_tag = u'!CaptureRegister'
    message_type = 'Register'


class Rfid(yaml.YAMLObject, Base):
    __metaclass__ = CustomMetaClass
    PROTOBUF_CLASS = orwell.messages.robot_pb2.Rfid
    yaml_tag = u'!Rfid'


class CaptureRfid(yaml.YAMLObject, Capture):
    PROTOBUF_CLASS = orwell.messages.robot_pb2.Rfid
    yaml_tag = u'!CaptureRfid'
    message_type = 'Rfid'


class ServerRobotState(yaml.YAMLObject, Base):
    __metaclass__ = CustomMetaClass
    PROTOBUF_CLASS = orwell.messages.robot_pb2.ServerRobotState
    yaml_tag = u'!ServerRobotState'


class CaptureServerRobotState(yaml.YAMLObject, Capture):
    PROTOBUF_CLASS = orwell.messages.robot_pb2.ServerRobotState
    yaml_tag = u'!CaptureServerRobotState'
    message_type = 'ServerRobotState'


class Access(yaml.YAMLObject, Base):
    __metaclass__ = CustomMetaClass
    PROTOBUF_CLASS = orwell.messages.server_game_pb2.Access
    yaml_tag = u'!Access'


class CaptureAccess(yaml.YAMLObject, Capture):
    PROTOBUF_CLASS = orwell.messages.server_game_pb2.Access
    yaml_tag = u'!CaptureAccess'
    message_type = 'Access'


class GameState(yaml.YAMLObject, Base):
    __metaclass__ = CustomMetaClass
    PROTOBUF_CLASS = orwell.messages.server_game_pb2.GameState
    yaml_tag = u'!GameState'


class CaptureGameState(yaml.YAMLObject, Capture):
    PROTOBUF_CLASS = orwell.messages.server_game_pb2.GameState
    yaml_tag = u'!CaptureGameState'
    message_type = 'GameState'


class Goodbye(yaml.YAMLObject, Base):
    __metaclass__ = CustomMetaClass
    PROTOBUF_CLASS = orwell.messages.server_game_pb2.Goodbye
    yaml_tag = u'!Goodbye'


class CaptureGoodbye(yaml.YAMLObject, Capture):
    PROTOBUF_CLASS = orwell.messages.server_game_pb2.Goodbye
    yaml_tag = u'!CaptureGoodbye'
    message_type = 'Goodbye'


class Registered(yaml.YAMLObject, Base):
    __metaclass__ = CustomMetaClass
    PROTOBUF_CLASS = orwell.messages.server_game_pb2.Registered
    yaml_tag = u'!Registered'


class CaptureRegistered(yaml.YAMLObject, Capture):
    PROTOBUF_CLASS = orwell.messages.server_game_pb2.Registered
    yaml_tag = u'!CaptureRegistered'
    message_type = 'Registered'


class Start(yaml.YAMLObject, Base):
    __metaclass__ = CustomMetaClass
    PROTOBUF_CLASS = orwell.messages.server_game_pb2.Start
    yaml_tag = u'!Start'


class CaptureStart(yaml.YAMLObject, Capture):
    PROTOBUF_CLASS = orwell.messages.server_game_pb2.Start
    yaml_tag = u'!CaptureStart'
    message_type = 'Start'


class Stop(yaml.YAMLObject, Base):
    __metaclass__ = CustomMetaClass
    PROTOBUF_CLASS = orwell.messages.server_game_pb2.Stop
    yaml_tag = u'!Stop'


class CaptureStop(yaml.YAMLObject, Capture):
    PROTOBUF_CLASS = orwell.messages.server_game_pb2.Stop
    yaml_tag = u'!CaptureStop'
    message_type = 'Stop'


class Team(yaml.YAMLObject, Base):
    __metaclass__ = CustomMetaClass
    PROTOBUF_CLASS = orwell.messages.server_game_pb2.Team
    yaml_tag = u'!Team'


class CaptureTeam(yaml.YAMLObject, Capture):
    PROTOBUF_CLASS = orwell.messages.server_game_pb2.Team
    yaml_tag = u'!CaptureTeam'
    message_type = 'Team'


class Welcome(yaml.YAMLObject, Base):
    __metaclass__ = CustomMetaClass
    PROTOBUF_CLASS = orwell.messages.server_game_pb2.Welcome
    yaml_tag = u'!Welcome'


class CaptureWelcome(yaml.YAMLObject, Capture):
    PROTOBUF_CLASS = orwell.messages.server_game_pb2.Welcome
    yaml_tag = u'!CaptureWelcome'
    message_type = 'Welcome'


class GetAccess(yaml.YAMLObject, Base):
    __metaclass__ = CustomMetaClass
    PROTOBUF_CLASS = orwell.messages.server_web_pb2.GetAccess
    yaml_tag = u'!GetAccess'


class CaptureGetAccess(yaml.YAMLObject, Capture):
    PROTOBUF_CLASS = orwell.messages.server_web_pb2.GetAccess
    yaml_tag = u'!CaptureGetAccess'
    message_type = 'GetAccess'


class GetGameState(yaml.YAMLObject, Base):
    __metaclass__ = CustomMetaClass
    PROTOBUF_CLASS = orwell.messages.server_web_pb2.GetGameState
    yaml_tag = u'!GetGameState'


class CaptureGetGameState(yaml.YAMLObject, Capture):
    PROTOBUF_CLASS = orwell.messages.server_web_pb2.GetGameState
    yaml_tag = u'!CaptureGetGameState'
    message_type = 'GetGameState'


# [[[end]]]

if ("__main__" == __name__):
    print(generate())
