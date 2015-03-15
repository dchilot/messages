from nose.tools import assert_equal
#from nose.tools import assert_true
#from nose.tools import assert_false
from nose.tools import assert_raises
import unittest
import orwell.yaml2protobuf as y2p
import pprint
import yaml
import orwell.messages.controller_pb2 as pb_controller
from pbjson.pbjson import pb2dict
from pbjson.pbjson import dict2pb


class MainTest(unittest.TestCase):
    def test_1(self):
        """Simple test with default value."""
        name = "Test"
        yaml_content = """
message: !Hello
    message:
        name: {name}
""".format(name=name)
        data = yaml.load(yaml_content)
        hello = data["message"]
        assert_equal(hello.name, name)
        payload = hello.protobuf_message.SerializeToString()
        message2 = pb_controller.Hello()
        message2.ParseFromString(payload)
        assert(message2.name == name)
        assert(message2.ready)

    def test_2(self):
        """Simple test with default value overriden."""
        name = "Test"
        ready = False
        yaml_content = """
message: !Hello
    message:
        name: {name}
        ready: {ready}
""".format(name=name, ready=ready)
        data = yaml.load(yaml_content)
        hello = data["message"]
        assert_equal(hello.name, name)
        payload = hello.protobuf_message.SerializeToString()
        message2 = pb_controller.Hello()
        message2.ParseFromString(payload)
        assert(message2.name == name)
        assert(message2.ready == ready)

    def test_3(self):
        """Play with the underlying library (not really a test)."""
        message = pb_controller.Hello()
        name = "JAMBON"
        message.name = name
        dico = pb2dict(message)
        dico_str = str(dico)
        message = pb_controller.Input()
        message.move.left = 0.2
        message.move.right = -0.5
        message.fire.weapon1 = False
        message.fire.weapon2 = True
        dico = pb2dict(message)
        dico_str = str(dico)
        message2 = dict2pb(pb_controller.Input, dico)
        assert(message2.move.left == 0.2)
        assert(message2.move.right == -0.5)
        assert(not message2.fire.weapon1)
        assert(message2.fire.weapon2)
        
    def test_4(self):
        """Nested message."""
        message = pb_controller.Input()
        message.move.left = 0.2
        message.move.right = -0.5
        message.fire.weapon1 = False
        message.fire.weapon2 = True
        yaml_content = """
message: !Input
    message:
        move:
            left: {left}
            right: {right}
        fire:
            weapon1: {weapon1}
            weapon2: {weapon2}
""".format(
            left=message.move.left,
            right=message.move.right,
            weapon1=message.fire.weapon1,
            weapon2=message.fire.weapon2)
        data = yaml.load(yaml_content)
        message2 = data["message"]
        assert_equal(message.move.left, message2.protobuf_message.move.left)
        assert_equal(message.move.right, message2.protobuf_message.move.right)
        assert_equal(message.fire.weapon1, message2.protobuf_message.fire.weapon1)
        assert_equal(message.fire.weapon2, message2.protobuf_message.fire.weapon2)

    def test_5(self):
        """Use the inline notation (json like)"""
        message = pb_controller.Input()
        message.move.left = 0.2
        message.move.right = -0.5
        message.fire.weapon1 = False
        message.fire.weapon2 = True
        yaml_content = """
message: !Input {{ "message": {{ "move": {{ "left": {left}, "right": {right} }},
"fire": {{ "weapon1": {weapon1}, "weapon2": {weapon2} }} }} }}""".format(
            left=message.move.left,
            right=message.move.right,
            weapon1=message.fire.weapon1,
            weapon2=message.fire.weapon2)
        data = yaml.load(yaml_content)
        message2 = data["message"]
        assert_equal(message.move.left, message2.protobuf_message.move.left)
        assert_equal(message.move.right, message2.protobuf_message.move.right)
        assert_equal(message.fire.weapon1, message2.protobuf_message.fire.weapon1)
        assert_equal(message.fire.weapon2, message2.protobuf_message.fire.weapon2)
