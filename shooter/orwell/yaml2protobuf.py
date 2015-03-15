import yaml
from pbjson.pbjson import pb2dict
from pbjson.pbjson import dict2pb

import orwell.messages.controller_pb2
import orwell.messages.robot_pb2
import orwell.messages.server_game_pb2
import orwell.messages.server_web_pb2

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
    def __init__(self, payload):
        self._message = self.PROTOBUF_CLASS()
        self._message.ParseFromString(payload)
        self.message = pb2dict(self._message)

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
#TEMPLATE = """
#class {name}(yaml.YAMLObject, Base):
#   __metaclass__ = CustomMetaClass
#   PROTOBUF_CLASS = {module}.{name}
#   yaml_tag = u'!{name}'
#"""
#
#def gen(class_description):
#   name, klass = class_description
#   module = klass.__module__
#   cog.outl(TEMPLATE.format(name=name, module=module))
#
#
#map(gen, inspect.getmembers(pb_controller, inspect.isclass))
#map(gen, inspect.getmembers(pb_robot, inspect.isclass))
#map(gen, inspect.getmembers(pb_server_game, inspect.isclass))
#map(gen, inspect.getmembers(pb_server_web, inspect.isclass))
# ]]]

class Fire(yaml.YAMLObject, Base):
   __metaclass__ = CustomMetaClass
   PROTOBUF_CLASS = orwell.messages.controller_pb2.Fire
   yaml_tag = u'!Fire'


class Hello(yaml.YAMLObject, Base):
   __metaclass__ = CustomMetaClass
   PROTOBUF_CLASS = orwell.messages.controller_pb2.Hello
   yaml_tag = u'!Hello'


class Input(yaml.YAMLObject, Base):
   __metaclass__ = CustomMetaClass
   PROTOBUF_CLASS = orwell.messages.controller_pb2.Input
   yaml_tag = u'!Input'


class Move(yaml.YAMLObject, Base):
   __metaclass__ = CustomMetaClass
   PROTOBUF_CLASS = orwell.messages.controller_pb2.Move
   yaml_tag = u'!Move'


class Colour(yaml.YAMLObject, Base):
   __metaclass__ = CustomMetaClass
   PROTOBUF_CLASS = orwell.messages.robot_pb2.Colour
   yaml_tag = u'!Colour'


class Register(yaml.YAMLObject, Base):
   __metaclass__ = CustomMetaClass
   PROTOBUF_CLASS = orwell.messages.robot_pb2.Register
   yaml_tag = u'!Register'


class Rfid(yaml.YAMLObject, Base):
   __metaclass__ = CustomMetaClass
   PROTOBUF_CLASS = orwell.messages.robot_pb2.Rfid
   yaml_tag = u'!Rfid'


class ServerRobotState(yaml.YAMLObject, Base):
   __metaclass__ = CustomMetaClass
   PROTOBUF_CLASS = orwell.messages.robot_pb2.ServerRobotState
   yaml_tag = u'!ServerRobotState'


class Access(yaml.YAMLObject, Base):
   __metaclass__ = CustomMetaClass
   PROTOBUF_CLASS = orwell.messages.server_game_pb2.Access
   yaml_tag = u'!Access'


class GameState(yaml.YAMLObject, Base):
   __metaclass__ = CustomMetaClass
   PROTOBUF_CLASS = orwell.messages.server_game_pb2.GameState
   yaml_tag = u'!GameState'


class Goodbye(yaml.YAMLObject, Base):
   __metaclass__ = CustomMetaClass
   PROTOBUF_CLASS = orwell.messages.server_game_pb2.Goodbye
   yaml_tag = u'!Goodbye'


class Registered(yaml.YAMLObject, Base):
   __metaclass__ = CustomMetaClass
   PROTOBUF_CLASS = orwell.messages.server_game_pb2.Registered
   yaml_tag = u'!Registered'


class Start(yaml.YAMLObject, Base):
   __metaclass__ = CustomMetaClass
   PROTOBUF_CLASS = orwell.messages.server_game_pb2.Start
   yaml_tag = u'!Start'


class Stop(yaml.YAMLObject, Base):
   __metaclass__ = CustomMetaClass
   PROTOBUF_CLASS = orwell.messages.server_game_pb2.Stop
   yaml_tag = u'!Stop'


class Team(yaml.YAMLObject, Base):
   __metaclass__ = CustomMetaClass
   PROTOBUF_CLASS = orwell.messages.server_game_pb2.Team
   yaml_tag = u'!Team'


class Welcome(yaml.YAMLObject, Base):
   __metaclass__ = CustomMetaClass
   PROTOBUF_CLASS = orwell.messages.server_game_pb2.Welcome
   yaml_tag = u'!Welcome'


class GetAccess(yaml.YAMLObject, Base):
   __metaclass__ = CustomMetaClass
   PROTOBUF_CLASS = orwell.messages.server_web_pb2.GetAccess
   yaml_tag = u'!GetAccess'


class GetGameState(yaml.YAMLObject, Base):
   __metaclass__ = CustomMetaClass
   PROTOBUF_CLASS = orwell.messages.server_web_pb2.GetGameState
   yaml_tag = u'!GetGameState'

# [[[end]]]
