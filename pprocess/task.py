"""
Módulo que gestiona las peticiones del usuario
"""

import asyncio
from itertools import chain
from typing import Any, List
from contextlib import suppress
from logs.logger import logger
from .exceptions import ResponseProcessException, ExternalProcessException
from .storage import RequestStorage
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
        self._chunk_requests = chunk_requests if chunk_requests > 0 else 1
        # Se inician parámetros internos
        self._request_storage = RequestStorage(time_chunk_requests)
        self._pool_process = PoolProcess(controller, num_processes, max_num_process)
        self._task_request_manager: asyncio.Task = None
        self._task_responses_manager: asyncio.Task = None

    async def start(self) -> None:
        """Se inicia el procesador de tareas.
        """
        logger.info("Iniciar procesamiento de tareas")
        check_id = checkpoint("Iniciar procesamiento de tareas")
        # Se cargan procesos. Uno solo se mantiene mientras esté activo el servidor, el resto son flexibles
        await self._pool_process.start()
        # Se inician los controladores en hilos independientes
        self._task_request_manager = asyncio.Task(self._request_manager())
        self._task_responses_manager = asyncio.Task(self._responses_manager())
        checkpoint(check_id=check_id)

    async def close(self) -> None:
        """Se cierra el rpcoesador de tareas
        """
        logger.info("Cerrar procesamiento de tareas")
        check_id = checkpoint("Cerrar procesamiento de tareas")
        self._task_request_manager.cancel()
        self._task_responses_manager.cancel()
        with suppress(asyncio.CancelledError):
            await self._task_request_manager
            await self._task_responses_manager
        await self._pool_process.close()
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
        r_id, queue_task = await self._request_storage.add(input_data)
        try:
            result, error = await queue_task.get()
        except asyncio.exceptions.CancelledError as exc:
            await self._request_storage.remove(r_id)
            raise ExternalProcessException() from exc
        checkpoint(check_id=check_id)
        if error:
            raise ResponseProcessException(error)
        return result

    async def send_batch(self, inputs_data: List[Any]) -> Any:
        """Envia un lote de parámetros a los procesos para que lo procesen

        Args:
            input (Dict): Parámetros de entrada para procesar en el controller

        Returns:
            Any: Resultado de la ejecución del controller
        """
        check_id = checkpoint("Llega una requests a send_batch()")
        chunk_input = split_array(inputs_data, self._chunk_requests)
        coros = [self.send(input) for input in chunk_input]
        batches = await asyncio.gather(*coros)
        result = list(chain.from_iterable(batches))
        checkpoint(check_id=check_id)
        return result

    async def _request_manager(self) -> None:
        """Revisa si hay datos para procesar
        """
        while True:
            data = await self._request_storage.get_data()
            if data:
                chunk_data = split_array(data, self._chunk_requests)
                asyncio.Task(self._pool_process.put(chunk_data))

    async def _responses_manager(self) -> None:
        """Controlador de requests de los usuarios
        """
        while True:
            response = await self._pool_process.get()
            if response:
                process_id, r_ids, results, errors = response
                await self._request_storage.put(r_ids, results, errors)
