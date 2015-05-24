from nose.tools import assert_equal
#from nose.tools import assert_true
#from nose.tools import assert_false
from nose.tools import assert_raises
import unittest
import orwell.shooter.scenario as scen
import pprint
import yaml

class MainTest(unittest.TestCase):
    yaml_content = """
messages:
    - hello: !CaptureHello &hello
        destination: TEST1
        message:
            name: Player
    - welcome: !CaptureWelcome &welcome
        destination: "{id}"
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
                    id: '%welcome_id%'
    - !Thread
        in_socket: *pull_b
        out_socket: *push_a
        flow:
            - !Out
                message: *hello
            - !In
                message: *welcome
            - !Equal
                values:
                    - '%expected_welcome_id%'
                    - "{Welcome[-1].id}"
"""
    # not sure about keeping Capture ; format string could be enough
    alternate_end = """
            - !Equal
                values:
                    - '%expected_welcome_id%'
                    - !Capture
                        value: "{welcome[-1].id}"
                    - "{welcome[-1].id}"
"""

    @staticmethod
    def test_1():
        import sys
        correct_id = "123"
        yaml_content = MainTest.yaml_content.replace(
            "%welcome_id%", correct_id).replace(
                "%expected_welcome_id%", correct_id)
        scenario = scen.Scenario(yaml_content)
        sys.stderr.write("\n" + str(scenario._data) + "\n")
        scenario.build()
        scenario.step()
        scenario.step()
        scenario.step()
        scenario.step()
        scenario.step()
        scenario.terminate()

    @staticmethod
    def test_2():
        import sys
        correct_id = "123"
        wrong_id = "666"
        yaml_content = MainTest.yaml_content.replace(
            "%welcome_id%", correct_id).replace(
                "%expected_welcome_id%", wrong_id)
        scenario = scen.Scenario(yaml_content)
        sys.stderr.write("\n" + str(scenario._data) + "\n")
        scenario.build()
        scenario.step()
        scenario.step()
        scenario.step()
        try:
            scenario.step()
            thrown = False
        except Exception as expected_exception:
            thrown = True
        assert(thrown)
        scenario.terminate()


def main():
    MainTest.test_1()
    MainTest.test_2()

if ("__main__" == __name__):
    main()
