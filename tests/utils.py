"""_summary_"""

from pprocess.controller import Controller


class TestController(Controller):
    """_summary_
    """

    @classmethod
    def execute(cls, params):
        results = {}
        for param in params:
            method = param[1]['input']['method']
            input_data = param[1]['input']['input']
            results[param[0]]= method(input_data)
        #print(results)
        return results
