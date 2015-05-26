from nose.tools import assert_equal
#from nose.tools import assert_true
#from nose.tools import assert_false
from nose.tools import assert_raises
import unittest
import orwell.yaml2protobuf as y2p
import pprint
import yaml
import orwell.messages.controller_pb2 as pb_controller
import orwell.messages.robot_pb2 as pb_robot
import orwell.messages.server_game_pb2 as pb_server_game
import orwell.messages.server_web_pb2 as pb_server_web
from pbjson.pbjson import pb2dict
from pbjson.pbjson import dict2pb


class MainTest(unittest.TestCase):
    def test_1(self):
        """Simple test with default value."""
        name = "Test"
        yaml_content = """
message: !CaptureHello
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
message: !CaptureHello
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
message: !CaptureInput
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
message: !CaptureInput {{ "message": {{ "move": {{ "left": {left}, "right": {right} }},
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

    def test_6(self):
        import os
        import sys
        test_dir = os.path.dirname(os.path.realpath(__file__))
        with open(os.path.join(test_dir, "conf.yaml"), 'r') as input:
            data = yaml.load(input.read())
            sys.stderr.write(str(data) + "\n")
            for dico in data["messages"]:
                #sys.stderr.write(" " + str(dico) + "\n")
                for name, message in dico.items():
                    sys.stderr.write("  " + str(name) + "\n")
                    sys.stderr.write("  pb fields: " + str(message.protobuf_message.ListFields()) + "\n")
                    sys.stderr.write("  pb:\n")
                    sys.stderr.write("   " + "\n   ".join(str(message.protobuf_message).split("\n")) + "\n")
                    if ("register" == name):
                        message_register_in = message.protobuf_message
                    sys.stderr.write("   extracted = " + str(message.key_map) + "\n")
        message_register = pb_robot.Register()
        message_register.temporary_robot_id = "TEMPID1"
        message_register.video_url = "http://video.url:123"
        message_register.image = "this is an image of the robot"
        sys.stderr.write(str(message_register) + "\n")
        sys.stderr.write(str(dir(message_register)) + "\n")
        sys.stderr.write("fields: " + str(message_register.ListFields()) + "\n")
        sys.stderr.write(str(message_register == message_register_in) + "\n")
        sys.stderr.write(" " + str(message_register.temporary_robot_id) + "\n")
        sys.stderr.write(" " + str(message_register.video_url) + "\n")
        sys.stderr.write(" " + str(message_register.image) + "\n")
        message_registered = pb_server_game.Registered()
        message_registered.robot_id = "ROBOT1"
        message_registered.team = pb_server_game.RED
        sys.stderr.write(str(message_registered) + "\n")
        sys.stderr.write(" " + str(message_registered.robot_id) + "\n")
        sys.stderr.write(" " + str(message_registered.team) + "\n")

    @staticmethod
    def test_key_map():
        pb_message = pb_controller.Input()
        pb_message.move.left = 0.2
        pb_message.move.right = -0.5
        pb_message.fire.weapon1 = False
        pb_message.fire.weapon2 = True
        yaml_content = """
message: !CaptureInput
    destination: TEST1
    message:
        move:
            left: {left}
            right: "{{right}}"
        fire:
            weapon1: {weapon1}
            weapon2: {weapon2}
""".format(
            left=pb_message.move.left,
            weapon1=pb_message.fire.weapon1,
            weapon2=pb_message.fire.weapon2)
        data = yaml.load(yaml_content)
        message1 = data["message"]
        import sys
        sys.stderr.write("\n" + str(message1.key_map) + "\n")
        assert_equal(message1.key_map["/move/left"], pb_message.move.left)
        assert_equal(message1.key_map["/move/right"], '{right}')
        assert_equal(message1.key_map["/fire/weapon1"], pb_message.fire.weapon1)
        assert_equal(message1.key_map["/fire/weapon2"], pb_message.fire.weapon2)
        pb_message.move.left = 1.0
        message2 = y2p.Input(pb_message.SerializeToString())
        sys.stderr.write(str(message2.key_map) + "\n")
        assert_equal(message2.key_map["/move/left"], pb_message.move.left)
        assert_equal(message2.key_map["/move/right"], pb_message.move.right)
        assert_equal(message2.key_map["/fire/weapon1"], pb_message.fire.weapon1)
        assert_equal(message2.key_map["/fire/weapon2"], pb_message.fire.weapon2)
        diffs = message1.compute_differences(message2)
        sys.stderr.write(str(diffs) + "\n")
        assert_equal(
            [('@destination', 'TEST1', None), ('/move/left', 0.2, 1.0)],
            diffs)
        sys.stderr.write(str(message1.captured) + "\n")
        assert_equal([{'right': -0.5}], message1.captured)
        pb_message = message1.fill(message1.captured[-1])
        sys.stderr.write('filled:' + str(pb_message) + "\n")
        message2.protobuf_message.move.left = 0.2
        assert_equal(str(pb_message), str(message2.protobuf_message))
        assert_equal(pb_message, message2.protobuf_message)

def main():
    MainTest.test_key_map()

if ("__main__" == __name__):
    main()
