"""
Esta clase administra una serie de procesos
"""

import math
import asyncio
import threading
from typing import Dict, Any, List
from contextlib import suppress
from multiprocessing import Queue, Process, cpu_count, Pipe
from pprocess.controller import Controller
from pprocess.unique_instance import UniqueInstance
from pprocess.utils import find_small_missing_number, get_uid, split_array
from datetime import datetime


class RequestLevel:
    """_summary_
    """
    START: str = 'start'
    PROCESSING: str = 'processing'
    FINISHED: str = 'finished'


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

    async def close(self) -> None:
        """_summary_
        """
        _ = [self._close_process(p_id) for p_id in self.processes.keys()]
        self.task_request_manager.cancel()
        self.task_process_manager.cancel()
        with suppress(asyncio.CancelledError):
            await self.task_request_manager
            await self.task_process_manager

    def _close_process(self, process_id: Any) -> None:
        """_summary_

        Args:
            process_id (_type_): _description_
        """
        if process_id in self.processes and self.processes[process_id]['process'].is_alive():
            self.processes[process_id]['process'].terminate()

    def _start_process(self, keep: bool = False) -> None:
        """_summary_

        Args:
            keep (bool, optional): _description_. Defaults to False.
        """
        process_id = find_small_missing_number(self.processes.keys())
        parent_conn, child_conn = Pipe()
        process = Process(
            target=self.controller.worker,
            daemon=True,
            args=(process_id, child_conn, keep)
        )
        process.start()
        self.processes[process_id] = {
            'process': process,
            'parent_conn': parent_conn,
            'child_conn': child_conn,
            'res_manager': asyncio.Task(self._response_manager(process_id, parent_conn)),
            'count': 0
        }

    async def exe_task(self, input: List[Dict] | Dict) -> Any:
        """Procesa una tarea en el controller en un proceso aparte

        Args:
            input (Dict): Parámetros de entrada para procesar en el controller

        Returns:
            _type_: Resultado de la ejecución del controller
        """
        queue_task = asyncio.Queue()
        if isinstance(input, Dict):
            print(f"{datetime.now()}: Se procesa data simple")
            self.requests.append((input, queue_task))
        else:
            print(f"{datetime.now()}: Se procesa data multiple")
            chunk_input = split_array(input, self.chunk_requests)
            asyncio.Task(self._batch_process(chunk_input, queue_task))
        return await queue_task.get()

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

    async def _batch_process(self, inputs_data, queues):
        """_summary_
        """
        if not isinstance(queues, list):
            print(f"{datetime.now()}: Se envian datos por lotes para un solo cliente")
            r_id = get_uid()
            queue_batch_task = asyncio.Queue()
            self.batch_requests[r_id] = queue_batch_task
            for input_data in inputs_data:
                self._send_data_in_avaible_process(r_id, input_data)
            print(f"{datetime.now()}: Se envian {len(inputs_data)} datos")
            asyncio.Task(self._wait_batch_process(queues, queue_batch_task,len(inputs_data)))
        else:
            print(f"{datetime.now()}: Se envian datos por lotes para varios clientes")
            for input_data, queue_task in inputs_data, queues:
                r_id = get_uid()
                self.batch_requests[r_id] = queue_task
                self._send_data_in_avaible_process(r_id, input_data)

    async def _wait_batch_process(self, queue_task, queue_batch_task, size):
        """_summary_

        Args:
            queue_batch_task (_type_): _description_
            size (_type_): _description_
        """
        results = []
        for i in range(size):
            print(f"Procesar: {i}")
            results.extend(await queue_batch_task.get())
        return await queue_task.put(results)

    async def _response_manager(self, process_id, parent_conn):
        """_summary_

        Args:
            process_id (_type_): _description_
            parent_conn (_type_): _description_
        """
        while True:
            if parent_conn.poll():
                r_id, result = parent_conn.recv()
                self.processes[process_id]['count'] -= 1
                await self.batch_requests[r_id].put(result)
            await asyncio.sleep(0)

    def _send_data_in_avaible_process(self, r_id, input_data):
        """_summary_

        Args:
            r_id (_type_): _description_
            input_data (_type_): _description_
        """
        index = min(self.processes, key=lambda x: self.processes[x]['count'])
        self.processes[index]['parent_conn'].send((r_id, input_data))
        self.processes[index]['count'] += 1

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
