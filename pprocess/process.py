"""
Módulo que contiene la clase PoolProcess.
"""

import asyncio
from contextlib import suppress
import queue
from multiprocessing import Process, Queue, cpu_count
import time
from typing import Any, Dict, List
import psutil
from logs.logger import logger
from .worker import Worker
from .utils.utils import find_small_missing_number

TIME_WAIT_TO_CREATE_NEW_PROCESS = 60*2  # 2 minutos
TIME_WAIT_TO_CHECK_CPU = 1  # 1 segundo
MAX_CPU_USAGE = 70  # 70%


class PoolProcess():
    """Clase que gestiona un pool de procesos en forma permanente.
    """

    def __init__(self, controller: Worker, num_processes: int, max_num_process: int):
        self._n: int = 1 if num_processes < 1 else num_processes
        self._max_num_process = max_num_process if max_num_process < cpu_count() else cpu_count()
        self._controller = controller
        self._input_queue = Queue()
        self._output_queue = Queue()
        self._processes: Dict[int, Dict] = {}
        self._task_process_manager: asyncio.Task = None

    def _close_process(self, process_id: Any) -> None:
        """Cierra un proceso por su ID

        Args:
            process_id (_type_): ID del proceso a cerrar
        """
        if process_id in self._processes and self._processes[process_id]['process'].is_alive():
            self._processes[process_id]['process'].terminate()
            logger.info("Se fuerza el cierre del proceso %i", process_id)

    def _start_process(self, keep: bool = False) -> None:
        """Inicia un proceso.

        Args:
            keep (bool, optional): Indica si el proceso se mantiene vivo, sin importar lo que pida el
            gestor de procesos. Por default es False (El proceso puee cerrarse).
        """
        process_id = find_small_missing_number(self._processes.keys())
        process = Process(
            target=self._controller.loop,
            daemon=True,
            args=(process_id, self._input_queue, self._output_queue, keep)
        )
        process.start()
        self._processes[process_id] = {
            'process': process,
            'measure': psutil.Process(process.pid)
        }

    async def start(self):
        """Inicia la ejecución del controlador de procesos
        """
        logger.info("Se inicia el pool de procesos")
        self._task_process_manager = asyncio.Task(self._process_manager())
        for i in range(self._n):
            self._start_process(keep=True if i == 0 else False)

    async def close(self) -> None:
        """Cierra todas las ejecuciones del controlador de procesos.
        """
        for p_id in self._processes:
            self._close_process(p_id)
        self._input_queue.close()
        self._output_queue.close()
        self._task_process_manager.cancel()
        with suppress(asyncio.CancelledError):
            await self._task_process_manager
        logger.info("Se cierra el pool de procesos")

    async def put(self, data: List[Any] | Any):
        """Envia datos a los procesos

        Args:
            data (_type_): Datos a enviar
        """
        data = data if isinstance(data, list) else [data]
        for d in data:
            self._input_queue.put(d)
            await asyncio.sleep(0)

    async def get(self) -> Any | None:
        """Devuleve un dato de algún proceso.

        Returns:
            _type_: _description_
        """
        try:
            await asyncio.sleep(0)
            return self._output_queue.get(timeout=0.001)
        except queue.Empty:
            return

    async def _get_avg_usage_cpu(self, cpu_qty:int)->float:
        """Devulelve el consumo promedio de todos los procesos activos.

        Args:
            cpu_qty (int): Cantiad de cpus activos.
        Returns:
            float: Promedio de consumo.
        """
        cpu_avg = 0
        for p_id, values in list(self._processes.items()):
            if not values['process'].is_alive():
                del self._processes[p_id]
            else:
                cpu_percent = self._processes[p_id]['measure'].cpu_percent(interval=0)
                cpu_avg += cpu_percent
                await asyncio.sleep(0)
        return cpu_avg/cpu_qty

    def _check_processes_capacity(self, time_cpu_max:float, cpu_qty:int)->bool:
        """Revisa si es tiempo de crear un nuevo proceso y si ya se llegó a la máxima cantidad de procesos posibles.

        Args:
            time_cpu_max (float): Tiempo que las cpu llevan trabajando al máximo.
            cpu_qty (int): Cantidad de procesos actuales.

        Returns:
            bool: True si hay que crear un nuevo proceso y False si hay que esperar.
        """
        return (time.time()-time_cpu_max) >= TIME_WAIT_TO_CREATE_NEW_PROCESS and \
            cpu_qty < self._max_num_process

    async def _process_manager(self) -> None:
        """Controlador de los procesos que se crean y destruyen.
        """
        time_cpu_max = 0
        while True:
            await asyncio.sleep(TIME_WAIT_TO_CHECK_CPU)
            cpu_qty = len(self._processes.keys())
            all_cpu_usage = await self._get_avg_usage_cpu(cpu_qty)
            if all_cpu_usage < MAX_CPU_USAGE:
                time_cpu_max = 0
                continue
            if time_cpu_max == 0:
                time_cpu_max = time.time()
                continue
            if self._check_processes_capacity(time_cpu_max, cpu_qty):
                self._start_process()
                time_cpu_max = 0
