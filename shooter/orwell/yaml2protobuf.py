import re

import yaml
from pbjson.pbjson import pb2dict
from pbjson.pbjson import dict2pb

import orwell.messages.controller_pb2
import orwell.messages.robot_pb2
import orwell.messages.server_game_pb2
import orwell.messages.server_web_pb2

import google.protobuf.descriptor as pb_descriptor

from . import messages


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
        meta = type(name, tuple(metas), dict(combined_metas = metas))

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
            first  = True
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
        setattr(instance, 'captured', [])
        # !CaptureMessage -> !Message
        setattr(
            instance,
            'captured_yaml_tag',
            instance.yaml_tag.replace('!Capture', '!'))
        return instance

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


    def compute_differences(self, other):
        differences = []
        captured = {}
        if (self.captured_yaml_tag != other.yaml_tag):
            differences.append(("@name", self.captured_yaml_tag, other.yaml_tag))
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
        return differences


# [[[cog
#import cog
#
#import inspect
#
#import orwell.messages.controller_pb2 as pb_controller
#import orwell.messages.robot_pb2 as pb_robot
#import orwell.messages.server_game_pb2 as pb_server_game
#import orwell.messages.server_web_pb2 as pb_server_web
#
#TEMPLATE = """class {name}(yaml.YAMLObject, Base):
#   __metaclass__ = CustomMetaClass
#   PROTOBUF_CLASS = {module}.{name}
#   yaml_tag = u'!{name}'
#
#
#class Capture{name}(yaml.YAMLObject, Capture):
#   yaml_tag = u'!Capture{name}'
#
#"""
#
#def gen(class_description):
#   name, klass = class_description
#   module = klass.__module__
#   cog.outl(TEMPLATE.format(name=name, module=module))
#
#
#cog.outl("\n")
#map(gen, inspect.getmembers(pb_controller, inspect.isclass))
#map(gen, inspect.getmembers(pb_robot, inspect.isclass))
#map(gen, inspect.getmembers(pb_server_game, inspect.isclass))
#map(gen, inspect.getmembers(pb_server_web, inspect.isclass))
# ]]]


class Fire(yaml.YAMLObject, Base):
   __metaclass__ = CustomMetaClass
   PROTOBUF_CLASS = orwell.messages.controller_pb2.Fire
   yaml_tag = u'!Fire'


class CaptureFire(yaml.YAMLObject, Capture):
   yaml_tag = u'!CaptureFire'


class Hello(yaml.YAMLObject, Base):
   __metaclass__ = CustomMetaClass
   PROTOBUF_CLASS = orwell.messages.controller_pb2.Hello
   yaml_tag = u'!Hello'


class CaptureHello(yaml.YAMLObject, Capture):
   yaml_tag = u'!CaptureHello'


class Input(yaml.YAMLObject, Base):
   __metaclass__ = CustomMetaClass
   PROTOBUF_CLASS = orwell.messages.controller_pb2.Input
   yaml_tag = u'!Input'


class CaptureInput(yaml.YAMLObject, Capture):
   yaml_tag = u'!CaptureInput'


class Move(yaml.YAMLObject, Base):
   __metaclass__ = CustomMetaClass
   PROTOBUF_CLASS = orwell.messages.controller_pb2.Move
   yaml_tag = u'!Move'


class CaptureMove(yaml.YAMLObject, Capture):
   yaml_tag = u'!CaptureMove'


class Colour(yaml.YAMLObject, Base):
   __metaclass__ = CustomMetaClass
   PROTOBUF_CLASS = orwell.messages.robot_pb2.Colour
   yaml_tag = u'!Colour'


class CaptureColour(yaml.YAMLObject, Capture):
   yaml_tag = u'!CaptureColour'


class Register(yaml.YAMLObject, Base):
   __metaclass__ = CustomMetaClass
   PROTOBUF_CLASS = orwell.messages.robot_pb2.Register
   yaml_tag = u'!Register'


class CaptureRegister(yaml.YAMLObject, Capture):
   yaml_tag = u'!CaptureRegister'


class Rfid(yaml.YAMLObject, Base):
   __metaclass__ = CustomMetaClass
   PROTOBUF_CLASS = orwell.messages.robot_pb2.Rfid
   yaml_tag = u'!Rfid'


class CaptureRfid(yaml.YAMLObject, Capture):
   yaml_tag = u'!CaptureRfid'


class ServerRobotState(yaml.YAMLObject, Base):
   __metaclass__ = CustomMetaClass
   PROTOBUF_CLASS = orwell.messages.robot_pb2.ServerRobotState
   yaml_tag = u'!ServerRobotState'


class CaptureServerRobotState(yaml.YAMLObject, Capture):
   yaml_tag = u'!CaptureServerRobotState'


class Access(yaml.YAMLObject, Base):
   __metaclass__ = CustomMetaClass
   PROTOBUF_CLASS = orwell.messages.server_game_pb2.Access
   yaml_tag = u'!Access'


class CaptureAccess(yaml.YAMLObject, Capture):
   yaml_tag = u'!CaptureAccess'


class GameState(yaml.YAMLObject, Base):
   __metaclass__ = CustomMetaClass
   PROTOBUF_CLASS = orwell.messages.server_game_pb2.GameState
   yaml_tag = u'!GameState'


class CaptureGameState(yaml.YAMLObject, Capture):
   yaml_tag = u'!CaptureGameState'


class Goodbye(yaml.YAMLObject, Base):
   __metaclass__ = CustomMetaClass
   PROTOBUF_CLASS = orwell.messages.server_game_pb2.Goodbye
   yaml_tag = u'!Goodbye'


class CaptureGoodbye(yaml.YAMLObject, Capture):
   yaml_tag = u'!CaptureGoodbye'


class Registered(yaml.YAMLObject, Base):
   __metaclass__ = CustomMetaClass
   PROTOBUF_CLASS = orwell.messages.server_game_pb2.Registered
   yaml_tag = u'!Registered'


class CaptureRegistered(yaml.YAMLObject, Capture):
   yaml_tag = u'!CaptureRegistered'


class Start(yaml.YAMLObject, Base):
   __metaclass__ = CustomMetaClass
   PROTOBUF_CLASS = orwell.messages.server_game_pb2.Start
   yaml_tag = u'!Start'


class CaptureStart(yaml.YAMLObject, Capture):
   yaml_tag = u'!CaptureStart'


class Stop(yaml.YAMLObject, Base):
   __metaclass__ = CustomMetaClass
   PROTOBUF_CLASS = orwell.messages.server_game_pb2.Stop
   yaml_tag = u'!Stop'


class CaptureStop(yaml.YAMLObject, Capture):
   yaml_tag = u'!CaptureStop'


class Team(yaml.YAMLObject, Base):
   __metaclass__ = CustomMetaClass
   PROTOBUF_CLASS = orwell.messages.server_game_pb2.Team
   yaml_tag = u'!Team'


class CaptureTeam(yaml.YAMLObject, Capture):
   yaml_tag = u'!CaptureTeam'


class Welcome(yaml.YAMLObject, Base):
   __metaclass__ = CustomMetaClass
   PROTOBUF_CLASS = orwell.messages.server_game_pb2.Welcome
   yaml_tag = u'!Welcome'


class CaptureWelcome(yaml.YAMLObject, Capture):
   yaml_tag = u'!CaptureWelcome'


class GetAccess(yaml.YAMLObject, Base):
   __metaclass__ = CustomMetaClass
   PROTOBUF_CLASS = orwell.messages.server_web_pb2.GetAccess
   yaml_tag = u'!GetAccess'


class CaptureGetAccess(yaml.YAMLObject, Capture):
   yaml_tag = u'!CaptureGetAccess'


class GetGameState(yaml.YAMLObject, Base):
   __metaclass__ = CustomMetaClass
   PROTOBUF_CLASS = orwell.messages.server_web_pb2.GetGameState
   yaml_tag = u'!GetGameState'


class CaptureGetGameState(yaml.YAMLObject, Capture):
   yaml_tag = u'!CaptureGetGameState'


# [[[end]]]
