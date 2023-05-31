"""_summary_"""

from pprocess.controller import Controller


def method(value):
    """_summary_
    """
    result = 0
    for _ in range(1000000):
        result += value*3
    return result


class TestController(Controller):
    """_summary_
    """

    @classmethod
    def execute(cls, params):
        results = []
        for param in params:
            results.append(method(param))
        # print(results)
        return results
