"""
Esta clase administra una serie de procesos
"""

import asyncio
from datetime import datetime
from itertools import chain
from typing import Dict, Any, List
from contextlib import suppress
from pprocess.controller import Controller
from pprocess.process import PoolProcess
from pprocess.unique_instance import UniqueInstance
from pprocess.utils import get_uid, split_array


times_storage = []


def log(msg, add_time=True):
    t = datetime.now()
    elapsed = 0 if not times_storage else round((t-times_storage[-1]).total_seconds()*1000, 2)
    if add_time:
        times_storage.append(t)
    print(f"{t}: {msg} - ({elapsed} ms)")


class RequestLevel:
    """_summary_
    """
    START: str = 'start'
    PROCESSING: str = 'processing'
    FINISHED: str = 'finished'


'''
TODO
Cosas a revisar:

- Falta el manejo de errores
- Qué pasa con el cliente si una operación no se termina de procesar?
- Qué pasa con la aplicación si un cliente corta la comunicación?
- Calcular rendimiento para un controller dado. Probar editando:
    - Número de procesos
    - Tamaño de lote (chunk)
    - Tiempo de espera para armarun lote
    - Enviando múltiples peticiones simples
    - Enviando múltiples peticiones agrupadas
'''


class ParallelProcess(metaclass=UniqueInstance):
    """_summary_
    """

    def __init__(
        self,
        controller: Controller,
        num_processes: int = 1,
        max_num_process: int = 4,
        chunk_requests: int = 30,
        time_chunk_requests: float = 0.1,
    ) -> None:
        # Se guardan parámetros pasados por el usuario
        self.chunk_requests = chunk_requests
        self.time_chunk_requests = time_chunk_requests
        # Se inician parámetros internos
        self.requests: List[Dict[str, Any]] = []
        self.batch_requests: Dict[str:Any] = {}
        self.stop_request_manager = False
        self.stop_process_manager = False
        self.task_request_manager: asyncio.Task = None
        self.task_responses_manager: asyncio.Task = None
        self.pool_process = PoolProcess(controller, num_processes, max_num_process)
        self.lock = asyncio.Lock()

    async def start(self) -> None:
        """_summary_
        """
        # Se cargan procesos. Uno solo se mantiene mientras esté activo el servidor, el resto son flexibles
        await self.pool_process.start()
        # Se inician los controladores en hilos independientes
        self.task_request_manager = asyncio.Task(self._request_manager())
        self.task_responses_manager = asyncio.Task(self._responses_manager())

    async def close(self) -> None:
        """_summary_
        """
        self.task_request_manager.cancel()
        self.task_responses_manager.cancel()
        with suppress(asyncio.CancelledError):
            await self.task_request_manager
            await self.task_responses_manager
        await self.pool_process.close()

    async def exe_task(self, input: List[Dict] | Dict) -> Any:
        global times_storage
        """Procesa una tarea en el controller en un proceso aparte

        Args:
            input (Dict): Parámetros de entrada para procesar en el controller

        Returns:
            _type_: Resultado de la ejecución del controller
        """
        times_storage = []
        queue_task = asyncio.Queue()
        if isinstance(input, Dict):
            log("Llegan datos simples")
            self.requests.append((input, queue_task))
        else:
            log("Llegan datos multiples")
            chunk_input = split_array(input, self.chunk_requests)
            '''
            TODO
            En base a la cantidad de chunks, esperar a que llegen esa cantidad de respuestas por el
            objeto queue. De esta manera, no es necesario crear otro queue en _batch_process.
            Por otro lado, probar usando Event. Es más eficiente?. En este caso, el evento se usa
            solo para avisar que ya está el resultado y que ya puede retirarlo de la memoria.
            '''
            asyncio.Task(self._batch_process(chunk_input, queue_task))
            log("Se separan datos en lotes")
        result = await queue_task.get()
        log("Devuelvo datos")
        return result

    async def _batch_process(self, inputs_data, queues):
        """_summary_
        """
        if not isinstance(queues, list):
            log("Se preparan datos en lotes para un solo cliente")
            r_id = get_uid()
            queue_batch_task = asyncio.Queue()
            self.batch_requests[r_id] = queue_batch_task
            for i, input_data in enumerate(inputs_data):
                await self.pool_process.put((r_id, input_data, i))
            log(f"Se envian {len(inputs_data)} datos")
            results = await self._wait_batch_process(queue_batch_task, len(inputs_data))  # Punto de delay minimo
            await queues.put(results)
        else:
            log("Se envian datos por lotes para varios clientes")
            for input_data, queue_task in inputs_data, queues:
                r_id = get_uid()
                self.batch_requests[r_id] = queue_task
                await self.pool_process.put((r_id, input_data, 0))

    async def _wait_batch_process(self, queue, size: int):
        """_summary_

        Args:
            queue (_type_): _description_
            size (_type_): _description_
        """
        log("Empiezo espera")
        coros = [queue.get() for _ in range(size)]
        # Se espera que lleguen todos los resultados de cada lote, pertenciente a una request.
        batches = await asyncio.gather(*coros)
        log("Termino espera")
        batches = sorted(batches, key=lambda x: x[1])
        results, _ = zip(*batches)
        # Se juntan todos los resultados en un mismo array
        results = list(chain.from_iterable(results))
        log("Se ordenan datos")
        return results

    async def _request_manager(self) -> None:
        """_summary_
        """
        while True:
            if self.requests:
                await self.lock.acquire()
                try:
                    inputs_data, queues = zip(*self.requests)
                    asyncio.Task(self._batch_process(inputs_data, queues))
                    self.requests.clear()
                finally:
                    # Liberar el bloqueo
                    self.lock.release()
            try:
                # Espera un tiempo determinado por self.time_chunk_requests
                await asyncio.wait_for(asyncio.sleep(self.time_chunk_requests), timeout=self.time_chunk_requests)
            except asyncio.TimeoutError:
                pass

    async def _responses_manager(self) -> None:
        """Controlador de requests de los usuarios
        """
        while True:
            result = await self.pool_process.get()
            if result:
                process_id, r_id, result, index = result
                log("Llega data del proceso", add_time=False)
                await self.batch_requests[r_id].put((result, index))
