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
        name: "fake server"
        loop: False
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
        name: "fake client"
        loop: False
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

    @staticmethod
    def test_1():
        print("test_1")
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
        # make sure we move to the step receiving the message
        for i in range(5):
            scenario.step()
        scenario.terminate()

    @staticmethod
    def test_2():
        print("test_2")
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
            # make sure we move to the step receiving the message
            for i in range(5):
                scenario.step()
            thrown = False
            sys.stdout.write("No exception raised.\n")
        except Exception as expected_exception:
            thrown = (
                ("Failure at index 2 in thread 'fake client'.",)
                == expected_exception.args)
            if (not thrown):
                sys.stdout.write("Exception different from expectation.\n")
            print(expected_exception)
        assert(thrown)
        scenario.terminate()

    @staticmethod
    def test_3():
        print("test_3")
        import sys
        correct_id = "123"
        yaml_content = MainTest.yaml_content.replace(
            "%welcome_id%", correct_id).replace(
                "%expected_welcome_id%", correct_id)
        yaml_content = "\n".join(yaml_content.split("\n")[:-2])
        scenario = scen.Scenario(yaml_content)
        try:
            scenario.build()
            thrown = False
        except Exception as expected_exception:
            thrown = (
                ("Only {} value(s) found but 2 expected.".format(1),)
                == expected_exception.args)
            print(expected_exception)
        assert(thrown)
        scenario.terminate()


def main():
    MainTest.test_1()
    MainTest.test_2()
    MainTest.test_3()

if ("__main__" == __name__):
    main()
