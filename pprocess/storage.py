"""
Módulo que sirve gestionar las requests que llegan
"""
import asyncio
from typing import Dict, Any, List
from pprocess.utils.utils import get_uid


class RequestStorage():
    """Clase encargada de gestionar las requests que llegan del usuario.
    """

    def __init__(self, time_chunk_requests: int):
        self._time_chunk_requests: float = time_chunk_requests/1000
        self._buffer: Dict[Dict[str, Any]] = {}
        self._requests: Dict[Dict[str, Any]] = {}

    async def add(self, input: Any) -> asyncio.Queue:
        """Agrega al buffer de memoria un request del usuario

        Args:
            input (Any): Parámetros a ejecutar en el proceso

        Returns:
            asyncio.queue: Objeto Queue para esperar el resultado
        """
        r_id = get_uid()
        queue_task = asyncio.Queue()
        self._buffer[r_id] = {
            "input": input,
            "queue": queue_task
        }
        return r_id,queue_task

    async def remove(self, r_id:str)->None:
        """Remueve de la lista de requets y del buffer una tarea

        Args:
            r_id (str): ID de la tarea a remover
        """
        if r_id in self._buffer:
            del self._buffer[r_id]
            await asyncio.sleep(0)
        if r_id in self._requests:
            del self._requests[r_id]
            await asyncio.sleep(0)

    async def get_data(self) -> List[tuple]:
        """Devuleve los datos almacenados en memoria y limpia el buffer.

        Returns:
            List[tuple]: Datos en memoria
        """
        data = []
        await asyncio.sleep(self._time_chunk_requests)
        if bool(self._buffer):
            for r_id, values in list(self._buffer.items()):
                data.append((r_id, values['input']))
                # Se pasan los datos a una nueva variable para esperar las respuestas
                self._requests[r_id] = values['queue']
                del self._buffer[r_id]
        return data

    async def put(self, r_ids: List[str], results: List[Any], errors: List[Any]) -> None:
        """Envía el resultado al dueño original del queue y elimina la referencia en memoria.

        Args:
            r_id (str): ID de la request.
            result (Any): Resultado obtendio de los procesadores.
        """
        if not results:
            results=[None]*len(r_ids)
        if not errors:
            errors=[None]*len(r_ids)
        for r_id, result, error in zip(r_ids, results, errors):
            if r_id in self._requests:
                await self._requests[r_id].put((result, error))
                del self._requests[r_id]
