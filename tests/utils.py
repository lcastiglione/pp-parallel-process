"""Módulo con funciones utils para los tests"""

import time
from pprocess.worker import Worker


def method(value):
    """_summary_
    """
    result = 0
    for _ in range(20000):
        result += value
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
                    if p==-1:
                        raise Exception("Simulando error desde un proceso")
                    r.append(method(p))
                results.append(r)
            else:
                if param==-1:
                    raise Exception("Simulando error desde un proceso")
                if param==2:
                    time.sleep(1)
                if param==-2:
                    for i in range(20000):
                       results.append(method(i))
                    print("Termino tarea pesada")
                    continue
                results.append(method(param))
        # print(results)
        return results,None
