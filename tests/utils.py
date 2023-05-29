"""_summary_"""

from pprocess.controller import Controller


class TestController(Controller):
    """_summary_
    """

    @classmethod
    def execute(cls, params):
        results = {}
        for param in params:
            method = param['method']
            input_data = param['input']
            results[param['id']]= method(input_data)
        print(results)
        return results
