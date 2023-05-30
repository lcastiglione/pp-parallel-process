"""
Esta clase administra una serie de procesos
"""

import math
import asyncio
import time
import queue
from itertools import islice
from typing import Dict, Any, List
from contextlib import suppress
from multiprocessing import Queue, Process, cpu_count
from pprocess.controller import Controller
from pprocess.unique_instance import UniqueInstance
from pprocess.utils import find_small_missing_number, get_uid
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
        time_chunk_requests: float = 0.01,
    ) -> None:
        # Se guardan parámetros pasados por el usuario
        self._n: int = 1 if num_processes < 1 else num_processes
        self.controller = controller
        self.max_num_process = max_num_process if max_num_process < cpu_count() else cpu_count()
        self.chunk_requests = chunk_requests
        self.time_chunk_requests = time_chunk_requests
        # Se inician parámetros internos
        self.processes: Dict[int, Process] = {}
        self.requests: Dict[Any, Dict[str, Any]] = {}
        self.input_queue = Queue()
        self.output_queue = Queue()
        self.stop_request_manager = False
        self.stop_process_manager = False
        self.stop_responses_manager = False
        self.task_request_manager: asyncio.Task = None
        self.task_responses_manager: asyncio.Task = None
        self.task_process_manager: asyncio.Task = None

    async def start(self) -> None:
        """_summary_
        """
        # Se cargan procesos. Uno solo se mantiene mientras esté activo el servidor, el resto son flexibles
        self._start_process(keep=True)
        _ = [self._start_process() for _ in range(self._n - 1)]

        # Se inician los controladores en hilos independientes
        self.task_request_manager = asyncio.Task(self._request_manager())
        self.task_responses_manager = asyncio.Task(self._responses_manager())
        self.task_process_manager = asyncio.Task(self._process_manager())

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

    async def _responses_manager(self) -> None:
        """Controlador de requests de los usuarios
        """
        while True:
            try:
                results: Any = self.output_queue.get(timeout=0.001)
                print(f"{datetime.now()}: Llega data del proceso")
                for r_id, result in list(results.items()):
                    self.requests[r_id]['result'] = result
                    self.requests[r_id]['status'] = RequestLevel.FINISHED
                    # Avisa que ya se termino de procesar la consulta
                    self.requests[r_id]['event'].set()
            except queue.Empty:
                pass
            # Esta línea es necesaria para manetner la función asíncrona
            await asyncio.sleep(0)

    async def _request_manager(self) -> None:
        """_summary_
        """
        while True:
            # Se usa list() porque self.requests cambia dinámicamente, lo que afecta al bucle for.
            def check_data(item):
                status = item[1]['status'] == RequestLevel.START
                self.requests[item[0]]['status'] = RequestLevel.PROCESSING
                return status
            print(f"{datetime.now()}: Se procesa data")
            r_to_process = map(
                lambda item: (item[0], {**item[1], 'event': None}),
                filter(check_data, self.requests.items()))
            print(f"{datetime.now()}: Se lotea data")
            data = list(iter(lambda: tuple(islice(r_to_process, self.chunk_requests)), ()))
            print(f"{datetime.now()}: Se envia data a proceso")
            if len(data) > 0:
                _ = [self.input_queue.put(d) for d in data]

            try:
                # Espera un tiempo determinado por self.time_chunk_requests
                await asyncio.wait_for(asyncio.sleep(self.time_chunk_requests), timeout=self.time_chunk_requests)
            except asyncio.TimeoutError:
                pass

    async def _process_manager(self) -> None:
        """Controlador de los procesos que se crean y destruyen
        """
        while True:
            # Se limpia buffer de procesos que ya están muertos
            # Se usa list() porque self.processes cambia dinámicamente, lo que afecta al bucle for.
            for p_id, process in list(self.processes.items()):
                if p_id in self.processes and not process.is_alive():
                    self._close_process(p_id)
                    del self.processes[p_id]
            # Se obtienen parámetros actuales
            num_p = len(list(self.processes.keys()))
            num_r = len(list(self.requests.keys()))
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

    async def exe_task(self, input: Dict) -> Any:
        """Procesa una tarea en el controller en un proceso aparte

        Args:
            input (Dict): Parámetros de entrada para procesar en el controller

        Returns:
            _type_: Resultado de la ejecución del controller
        """
        request_id = get_uid()
        self.requests[request_id] = {
            'status': RequestLevel.START,
            'input': input,
            'event': asyncio.Event()}
        # Espera a que se termine de procesar la consulta
        await self.requests[request_id]['event'].wait()
        result = self.requests[request_id]['result']
        del self.requests[request_id]
        return result

    async def exe_batch_task(self, inputs: List[Dict]) -> List[Any]:
        """Procesa un lote de tareas en paralelo y devuelve todos los resultados juntos ordenados según el orden de `input_data`.

        Args:
            input_data (List[Any]): Parámetros de entrada del handler
            handler_id (str): ID del handler a ejecutar

        Returns:
            List[Any]: Lista de resultados de la ejecución del handler
        """
        '''
        Cambiar lógica. Si el usuario está enviando un lote de tareas a realizar, no requieren que cada una tenga un id y una tarea. En su lugar, crear lotes y asignarle un id a cada lote. Luego, en los procesos, procesar los lotes.
        '''
        print(f"{datetime.now()}: Llegan tareas")
        coroutines = [self.exe_task(input) for input in inputs]
        return await asyncio.gather(*coroutines)
