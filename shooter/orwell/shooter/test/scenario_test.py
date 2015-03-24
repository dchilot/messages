from nose.tools import assert_equal
#from nose.tools import assert_true
#from nose.tools import assert_false
from nose.tools import assert_raises
import unittest
import orwell.shooter.scenario as scen
import pprint
import yaml

class MainTest(unittest.TestCase):
    @staticmethod
    def test_1():
        import sys
        yaml_content = """
messages:
    - hello: !Hello &hello
        message:
            name: Player
    - welcome: !CaptureWelcome &welcome
        message:
            robot: Nono
            team: 1
            id: "{id}"
            video_address: "http://fake.com"
            video_port: 42

sockets:
    - !SocketPull &pull_a
        port: 9008
        bind: yes
    - !SocketPull &pull_b
        port: 9009
        bind: yes
    - !SocketPush &push_a
        port: 9008
    - !SocketPush &push_b
        port: 9009

threads:
    - !Thread
        in_socket: *pull_a
        out_socket: *push_b
        flow:
            - !In
                message: *hello
            - !Out
                message: *welcome
                arguments:
                    id: '123'
    - !Thread
        in_socket: *push_a
        out_socket: *pull_b
        flow:
            - !Out
                message: *hello
            - !In
                message: *welcome
            - !Equal
                values:
                    - '123'
                    - !Capture
                        value: "{welcome[-1].id}"
                    - "{welcome[-1].id}"
"""
        scenario = scen.Scenario(yaml_content)
        sys.stderr.write("\n" + str(scenario._data) + "\n")


def main():
    MainTest.test_1()

if ("__main__" == __name__):
    main()
