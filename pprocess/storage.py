"""
Módulo que sirve gestionar las requests que llegan
"""
import asyncio
from typing import Dict, Any, List
from pprocess.utils.utils import get_uid


class RequestsStorage():
    """Clase encargada de gestionar las requests que llegan del usuario.
    """

    def __init__(self, time_chunk_requests: int):
        self.time_chunk_requests: float = time_chunk_requests/1000
        self.buffer: Dict[Dict[str, Any]] = {}
        self.requests: Dict[Dict[str, Any]] = {}

    async def add(self, input: Any) -> asyncio.Queue:
        """Agrega al buffer de memoria un request del usuario

        Args:
            input (Any): Parámetros a ejecutar en el proceso

        Returns:
            asyncio.queue: Objeto Queue para esperar el resultado
        """
        r_id = get_uid()
        queue_task = asyncio.Queue()
        self.buffer[r_id] = {
            "input": input,
            "queue": queue_task
        }
        return queue_task

    async def get_data(self) -> List[tuple]:
        """Devuleve los datos almacenados en memoria y limpia el buffer.

        Returns:
            List[tuple]: Datos en memoria
        """
        data = []
        await asyncio.sleep(self.time_chunk_requests)
        if bool(self.buffer):
            for r_id, values in list(self.buffer.items()):
                data.append((r_id, values['input']))
                #Se pasan los datos a una nueva variable para esperar las respuestas
                self.requests[r_id] = values['queue']
                del self.buffer[r_id]
        return data

    async def put(self, r_id:str, result:Any)->None:
        """Envía el resultado al dueño original del queue y elimina la referencia en memoria.

        Args:
            r_id (str): ID de la request.
            result (Any): Resultado obtendio de los procesadores.
        """
        await self.requests[r_id].put(result)
        del self.requests[r_id]
