"""
Módulo que gestiona las peticiones del usuario
"""

import asyncio
from itertools import chain
from typing import Dict, Any, List
from contextlib import suppress
from logs.logger import logger
from .storage import RequestsStorage
from .worker import Worker
from .process import PoolProcess
from .utils.unique_instance import UniqueInstance
from .utils.performance import checkpoint
from .utils.utils import split_array


class TaskProcess(metaclass=UniqueInstance):
    """Clase que recibe y procesa las peticiones del usuario
    """

    def __init__(
        self,
        controller: Worker,
        num_processes: int = 1,
        max_num_process: int = 4,
        chunk_requests: int = 30,
        time_chunk_requests: int = 10,  # ms
    ) -> None:
        # Se guardan parámetros pasados por el usuario
        self.chunk_requests = chunk_requests if chunk_requests > 0 else 1
        # Se inician parámetros internos
        self.request_storage = RequestsStorage(time_chunk_requests)
        self.pool_process = PoolProcess(controller, num_processes, max_num_process)
        self.requests: List[Dict[str, Any]] = []
        self.batch_requests: Dict[str:Any] = {}
        self.task_request_manager: asyncio.Task = None
        self.task_responses_manager: asyncio.Task = None

    async def start(self) -> None:
        """Se inicia el procesador de tareas.
        """
        logger.info("Iniciar procesamiento de tareas")
        check_id = checkpoint("Iniciar procesamiento de tareas")
        # Se cargan procesos. Uno solo se mantiene mientras esté activo el servidor, el resto son flexibles
        await self.pool_process.start()
        # Se inician los controladores en hilos independientes
        self.task_request_manager = asyncio.Task(self._request_manager())
        self.task_responses_manager = asyncio.Task(self._responses_manager())
        checkpoint(check_id=check_id)

    async def close(self) -> None:
        """Se cierra el rpcoesador de tareas
        """
        logger.info("Cerrar procesamiento de tareas")
        check_id = checkpoint("Cerrar procesamiento de tareas")
        self.task_request_manager.cancel()
        self.task_responses_manager.cancel()
        with suppress(asyncio.CancelledError):
            await self.task_request_manager
            await self.task_responses_manager
        await self.pool_process.close()
        UniqueInstance.remove_instance(self.__class__)
        checkpoint(check_id=check_id)

    async def send(self, input_data: Any) -> Any:
        """Envia un parámetro a los procesos para que lo procesen

        Args:
            input (Dict): Parámetros de entrada para procesar en el controller

        Returns:
            Any: Resultado de la ejecución del controller
        """
        check_id = checkpoint("Llega una requests a send()")
        queue_task = await self.request_storage.add(input_data)
        result = await queue_task.get()
        checkpoint(check_id=check_id)
        return result

    async def send_batch(self, inputs_data: List[Any]) -> Any:
        """Envia un lote de parámetros a los procesos para que lo procesen

        Args:
            input (Dict): Parámetros de entrada para procesar en el controller

        Returns:
            Any: Resultado de la ejecución del controller
        """
        check_id = checkpoint("Llega una requests a send_batch()")
        chunk_input = split_array(inputs_data, self.chunk_requests)
        coros = [self.send(input) for input in chunk_input]
        batches = await asyncio.gather(*coros)
        result = list(chain.from_iterable(batches))
        checkpoint(check_id=check_id)
        return result

    async def _request_manager(self) -> None:
        """Revisa si hay datos para procesar
        """
        while True:
            data = await self.request_storage.get_data()
            if data:
                chunk_data = split_array(data, self.chunk_requests)
                asyncio.Task(self.pool_process.put(chunk_data))

    async def _responses_manager(self) -> None:
        """Controlador de requests de los usuarios
        """
        while True:
            result = await self.pool_process.get()
            if result:
                process_id, r_id, result = result
                await self.request_storage.put(r_id, result)
