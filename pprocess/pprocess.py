"""
Esta clase administra una serie de procesos
"""

import math
import asyncio
import queue
import threading
from typing import Dict, Any, List
from contextlib import suppress
from multiprocessing import Queue, Process, cpu_count, Pipe
from pprocess.controller import Controller
from pprocess.unique_instance import UniqueInstance
from pprocess.utils import find_small_missing_number, get_uid, split_array
from datetime import datetime
from itertools import chain

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
        self._n: int = 1 if num_processes < 1 else num_processes
        self.controller = controller
        self.max_num_process = max_num_process if max_num_process < cpu_count() else cpu_count()
        self.chunk_requests = chunk_requests
        self.time_chunk_requests = time_chunk_requests
        # Se inician parámetros internos
        self.processes: Dict[int, Process] = {}
        self.requests: List[Dict[str, Any]] = []
        self.batch_requests: Dict[str:Any] = {}
        self.input_queue = Queue()
        self.output_queue = Queue()
        self.stop_request_manager = False
        self.stop_process_manager = False
        self.task_request_manager: asyncio.Task = None
        self.task_process_manager: asyncio.Task = None
        self.lock = asyncio.Lock()

    async def start(self) -> None:
        """_summary_
        """
        # Se cargan procesos. Uno solo se mantiene mientras esté activo el servidor, el resto son flexibles
        self._start_process(keep=True)
        _ = [self._start_process() for _ in range(self._n - 1)]

        # Se inician los controladores en hilos independientes
        self.task_request_manager = asyncio.Task(self._request_manager())
        self.task_process_manager = asyncio.Task(self._process_manager())
        self.task_responses_manager = asyncio.Task(self._responses_manager())

    async def close(self) -> None:
        """_summary_
        """
        _ = [self._close_process(p_id) for p_id in self.processes]
        self.input_queue.close()
        self.output_queue.close()
        self.task_request_manager.cancel()
        self.task_process_manager.cancel()
        self.task_responses_manager.cancel()
        with suppress(asyncio.CancelledError):
            await self.task_request_manager
            await self.task_process_manager
            await self.task_responses_manager

    def _close_process(self, process_id: Any) -> None:
        """_summary_

        Args:
            process_id (_type_): _description_
        """
        if process_id in self.processes and self.processes[process_id].is_alive():
            self.processes[process_id].terminate()

    def _start_process(self, keep: bool = False) -> None:
        """_summary_

        Args:
            keep (bool, optional): _description_. Defaults to False.
        """
        process_id = find_small_missing_number(self.processes.keys())
        process = Process(
            target=self.controller.worker,
            daemon=True,
            args=(process_id, self.input_queue, self.output_queue, keep)
        )
        process.start()
        self.processes[process_id] = process

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
                self.input_queue.put((r_id, input_data, i))
            log(f"Se envian {len(inputs_data)} datos")
            results = await self._wait_batch_process(queue_batch_task, len(inputs_data))  # Punto de delay minimo
            await queues.put(results)
        else:
            log("Se envian datos por lotes para varios clientes")
            for input_data, queue_task in inputs_data, queues:
                r_id = get_uid()
                self.batch_requests[r_id] = queue_task
                self.input_queue.put((r_id, input_data, 0))

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
            try:
                process_id, r_id, result, index = self.output_queue.get(timeout=0.001)
                log("Llega data del proceso", add_time=False)
                await self.batch_requests[r_id].put((result, index))
            except queue.Empty:
                pass
            # Esta línea es necesaria para manetner la función asíncrona
            await asyncio.sleep(0)

    async def _process_manager(self) -> None:
        """Controlador de los procesos que se crean y destruyen
        """
        while True:
            # Se limpia buffer de procesos que ya están muertos
            # Se usa list() porque self.processes cambia dinámicamente, lo que afecta al bucle for.
            for p_id, process in list(self.processes.items()):
                if p_id in self.processes and not process['process'].is_alive():
                    self._close_process(p_id)
                    del self.processes[p_id]
            # Se obtienen parámetros actuales
            num_p = len(list(self.processes.keys()))
            num_r = len(self.requests)
            # Se calculan los procesos que se necesitan
            request_by_process = math.ceil(num_r / num_p)
            # Si la carga del servidor está bien, no se abren nuevos procesos
            if request_by_process > self.chunk_requests:
                num_new_p = math.ceil(num_r / self.chunk_requests)
                # No se pueden abrir máx procesos que el límite marcado
                if num_new_p > self.max_num_process:
                    num_new_p = self.max_num_process - num_p
                else:
                    num_new_p = num_new_p - num_p
                # Se abren nuevos porcesos
                _ = [self._start_process() for _ in range(num_new_p)]
            try:
                # Espera un tiempo determinado por self.time_chunk_requests
                await asyncio.wait_for(asyncio.sleep(1), timeout=1)
            except asyncio.TimeoutError:
                pass
