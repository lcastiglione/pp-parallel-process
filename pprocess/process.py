"""
Módulo que contiene la clase PoolProcess.
"""

import asyncio
from contextlib import suppress
import queue
from multiprocessing import Process, Queue, cpu_count
from typing import Any, Dict, List
import psutil
from logs.logger import logger
from .worker import Worker
from .utils.utils import find_small_missing_number


class PoolProcess():
    """Clase que gestiona un pool de procesos en forma permanente.
    """

    def __init__(self, controller: Worker, num_processes: int = 1, max_num_process: int = 4):
        self._n: int = 1 if num_processes < 1 else num_processes
        self.max_num_process = max_num_process if max_num_process < cpu_count() else cpu_count()
        self.controller = controller
        self.input_queue = Queue()
        self.output_queue = Queue()
        self.processes: Dict[int, Dict] = {}
        self.task_process_manager: asyncio.Task = None

    def _close_process(self, process_id: Any) -> None:
        """Cierra un proceso por su ID

        Args:
            process_id (_type_): ID del proceso a cerrar
        """
        if process_id in self.processes and self.processes[process_id]['process'].is_alive():
            self.processes[process_id]['process'].terminate()

    def _start_process(self, keep: bool = False) -> None:
        """Inicia un proceso.

        Args:
            keep (bool, optional): Indica si el proceso se mantiene vivo, sin importar lo que pida el
            gestor de procesos. Por default es False (El proceso puee cerrarse).
        """
        process_id = find_small_missing_number(self.processes.keys())
        process = Process(
            target=self.controller.loop,
            daemon=True,
            args=(process_id, self.input_queue, self.output_queue, keep)
        )
        process.start()
        self.processes[process_id] = {
            'process': process,
            'measure': psutil.Process(process.pid)
        }

    async def start(self):
        """Inicia la ejecución del controlador de procesos
        """
        logger.info("Se inicia el pool de procesos")
        self.task_process_manager = asyncio.Task(self._process_manager())
        for i in range(self._n):
            self._start_process(keep=True if i == 0 else False)

    async def close(self) -> None:
        """Cierra todas las ejecuciones del controlador de procesos.
        """
        for p_id in self.processes:
            self._close_process(p_id)
        self.input_queue.close()
        self.output_queue.close()
        self.task_process_manager.cancel()
        with suppress(asyncio.CancelledError):
            await self.task_process_manager
        logger.info("Se cierra el pool de procesos")

    async def put(self, data: List[Any] | Any):
        """Envia datos a los procesos

        Args:
            data (_type_): Datos a enviar
        """
        data = data if isinstance(data, list) else [data]
        for d in data:
            self.input_queue.put(d)
            await asyncio.sleep(0)

    async def get(self) -> Any | None:
        """Devuleve un dato de algún proceso.

        Returns:
            _type_: _description_
        """
        try:
            await asyncio.sleep(0)
            return self.output_queue.get(timeout=0.001)
        except queue.Empty:
            return

    async def _process_manager(self) -> None:
        """Controlador de los procesos que se crean y destruyen
        """
        # TODO
        # La idea es ir registrando los consumos de procesador. Si los consumos de los procesadores actuales es alto durante determinado
        # tiempo, se abren más procesos sino, se pueden cerrar (Ver cómo afecta al loop esto)
        # Posible método: Calcular el promedio del consumo actual de CPU y contar cuánto tiempo se mantiene por encima del 50%. Si es así,
        # se abre un nuevo proceso.
        # Se vuelve a repetir el cálculo hasta que se llegue al máximo de procesadores.
        # Lo mismo ocurre cuando no se está usando la CPU. Después de determinado tiempo se empiezan a cerrar procesos uno a uno hasta
        # llegar al mínimo
        while True:
            cpu_avg = 0
            for p_id, values in self.processes.items():
                if values['process'].is_alive():
                    cpu_percent = self.processes[p_id]['measure'].cpu_percent(interval=0)
                    cpu_avg += cpu_percent
            # print(f"Consumo promedio: {round(cpu_avg/len(self.processes), 2)}%")
            try:
                # Espera un tiempo determinado por self.time_chunk_requests
                await asyncio.wait_for(asyncio.sleep(0.1), timeout=0.1)
            except asyncio.TimeoutError:
                pass
