import yaml
from pbjson.pbjson import pb2dict
from pbjson.pbjson import dict2pb

import orwell.messages.controller_pb2 as pb_controller
import orwell.messages.robot_pb2 as pb_robot
import orwell.messages.server_game_pb2 as pb_server_game
import orwell.messages.server_web_pb2 as pb_server_web

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
# [[[end]]]

class Hello(yaml.YAMLObject, Base):
    __metaclass__ = CustomMetaClass
    PROTOBUF_CLASS = pb_controller.Hello
    yaml_tag = u'!Hello'


class Move(yaml.YAMLObject, Base):
    __metaclass__ = CustomMetaClass
    PROTOBUF_CLASS = pb_controller.Move
    yaml_tag = u'!Move'


class Fire(yaml.YAMLObject, Base):
    __metaclass__ = CustomMetaClass
    PROTOBUF_CLASS = pb_controller.Fire
    yaml_tag = u'!Fire'


class Input(yaml.YAMLObject, Base):
    __metaclass__ = CustomMetaClass
    PROTOBUF_CLASS = pb_controller.Input
    yaml_tag = u'!Input'


class ServerRobotState(yaml.YAMLObject, Base):
    __metaclass__ = CustomMetaClass
    PROTOBUF_CLASS = pb_robot.ServerRobotState
    yaml_tag = u'!ServerRobotState'

