from pprocess.worker import Worker

class ExampleWorker(Worker):

    @classmethod
    def load_config(cls):
        pass

    @classmethod
    def execute(cls, params):
        results = []
        errors = None
        for p in params:
            t=0
            for i in range(2000000):
                t+=p*i
            results.append(t)
        return results,errors #Se devuleven siempre dos valores: Los resultados y los errores. Si no hay errores es None.