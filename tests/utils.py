"""Módulo con funciones utils para los tests"""

import time
from pprocess.worker import Worker


def method(value):
    """_summary_
    """
    start =time.time()
    result = 0
    for _ in range(20000):
        result += value
    #print(f"Tiempo method: {time.time()-start}s")
    return result


class TestController(Worker):
    """_summary_
    """

    @classmethod
    def load_config(cls):
        pass

    @classmethod
    def execute(cls, params):
        results = []
        for param in params:
            if isinstance(param,list):
                r=[]
                for p in param:
                    r.append(method(p))
                results.append(r)
            else:
                print("Resultado simple",param)
                if param==-1:
                    raise Exception("Simulando error desde un proceso")
                results.append(method(param))
        # print(results)
        return results
