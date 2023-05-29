"""
Esta clase administra una serie de procesos
"""

import math
import asyncio
from typing import Dict, Any, List
from contextlib import suppress
from multiprocessing import Queue, Process, cpu_count
from pprocess.handler import Handler
from pprocess.unique_instance import UniqueInstance
from pprocess.utils import get_uid


class RequestLevel:
    """_summary_"""
    NEW: str = 'new'
    PROCESSING: str = 'processing'
    FINISHED: str = 'finished'


class ParallelProcess(metaclass=UniqueInstance):
    """_summary_"""

    def __init__(
        self,
        handler: Handler,
        num_processes: int = 1,
        max_num_process: int = 4,
        chunk_requests: int = 30,
        time_chunk_requests: float = 0.1,
    ) -> None:
        # Se guardan parámetros pasados por el usuario
        self._n: int = 1 if num_processes < 1 else num_processes
        self.handler = handler
        self.max_num_process = max_num_process if max_num_process < cpu_count() else cpu_count()
        self.chunk_requests = chunk_requests
        self.time_chunk_requests = time_chunk_requests
        # Se inician parámetros internos
        self.processes: Dict[Any, Process] = {}
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
        """_summary_"""
        # Se cargan procesos. Uno solo se mantiene mientras esté activo el servidor, el resto son flexibles
        self._start_process(keep=True)
        _ = [self._start_process() for _ in range(self._n - 1)]

        # Se inician los controladores en hilos independientes
        self.task_request_manager = asyncio.Task(self._request_manager())
        self.task_responses_manager = asyncio.Task(self._responses_manager())
        self.task_process_manager = asyncio.Task(self._process_manager())

    async def stop(self) -> None:
        """_summary_"""
        _ = [self._close_process(p_id) for p_id in self.processes]
        self.input_queue.close()
        self.output_queue.close()
        # log("Se cierran controladores")
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
            # log(f"Se cierra el proceso {process_id}")

    def _start_process(self, keep: bool = False) -> None:
        """_summary_

        Args:
            keep (bool, optional): _description_. Defaults to False.
        """
        process_id = get_uid()
        process = Process(
            target=self.handler.worker,
            daemon=True,
            args=(process_id, self.input_queue, self.output_queue, keep),
        )
        process.start()
        self.processes[process_id] = process
        # log(f"Se inicia el proceso {process_id}")

    async def _responses_manager(self) -> None:
        """ontrolador de requests de los usuarios"""
        # log("Se inicia el controlador de respuestas")
        while True:
            if not self.output_queue.empty():
                results, _ = self.output_queue.get_nowait()
                # log(f"LLegan {len(results)} resultados de proceso {p_id}")
                for r_id, result in results.items():
                    self.requests[r_id]['result'] = result
                    self.requests[r_id]['status'] = RequestLevel.FINISHED
            await asyncio.sleep(0.001)

    async def _request_manager(self) -> None:
        """_summary_"""
        # log("Se inicia el controlador de peticiones")
        while True:
            inputs = []
            for r_id, r_value in list(self.requests.items()):
                if r_value['status'] == RequestLevel.NEW:
                    self.requests[r_id]['status'] = RequestLevel.PROCESSING
                    # En vez de hacer un array, hacer un dict con el id como key
                    inputs.append({**r_value['input'].dict(), **{"id": r_id}})
            if len(inputs) > 0:
                # log(f"Se procesan {len(inputs)} peticiones de {len(list(self.requests.items()))}")
                for i in range(0, len(inputs), self.chunk_requests):
                    self.input_queue.put((inputs[i: i + self.chunk_requests]))
            await asyncio.sleep(self.time_chunk_requests)

    async def _process_manager(self) -> None:
        """Controlador de los procesos que se crean y destruyen"""
        # log("Se inicia el controlador de procesos")
        while True:
            # Se limpia buffer de procesos que ya están muertos
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
            await asyncio.sleep(0.001)

    async def _wait_to_result(self, request_id: Any) -> None:
        """Función para obtener el resultado de una solicitud

        Args:
            request_id (_type_): _description_
        """
        while True and not self.stop_request_manager:
            if self.requests[request_id]['status'] == RequestLevel.FINISHED:
                break
            await asyncio.sleep(0.001)

    async def process(self, input_value: Any, handler_id: str) -> Any:
        """Procesa un handler en un proceso aparte

        Args:
            input_value (Any): Parámetros de entrada del handler
            handler_id (str): ID del handler a ejecutar

        Returns:
            _type_: Resultado de la ejecución del handler
        """
        request_id=None
        # log(f"Llega solicitud: {handler_id}")
        self.requests[request_id] = {
            'status': RequestLevel.NEW, 'input': input_value}
        await self._wait_to_result(request_id)
        result = self.requests[request_id]['result']
        del self.requests[request_id]
        return result

    async def process_batch(self, input_data: List[Any], handler_id: str) -> List[Any]:
        """Procesa un lote de tareas en paralelo y devuelve todos los resultados juntos ordenados según el orden de `input_data`.

        Args:
            input_data (List[Any]): Parámetros de entrada del handler
            handler_id (str): ID del handler a ejecutar

        Returns:
            List[Any]: Lista de resultados de la ejecución del handler
        """
