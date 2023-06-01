"""
Módulo que contiene la clase PoolProcess.
"""


import asyncio
from contextlib import suppress
import queue
from multiprocessing import Process, Queue, cpu_count
from typing import Any, Dict
import psutil
from .controller import Controller
from .utils.utils import find_small_missing_number


class PoolProcess():
    """Clase que representa un pool de procesos.
    """

    def __init__(self, controller: Controller, num_processes: int = 1, max_num_process: int = 4):
        self._n: int = 1 if num_processes < 1 else num_processes
        self.max_num_process = max_num_process if max_num_process < cpu_count() else cpu_count()
        self.controller = controller
        self.input_queue = Queue()
        self.output_queue = Queue()
        self.processes: Dict[int, Dict] = {}
        self.task_process_manager: asyncio.Task = None

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
        process = Process(
            target=self.controller.worker,
            daemon=True,
            args=(process_id, self.input_queue, self.output_queue, keep)
        )
        process.start()
        self.processes[process_id] = {
            'process': process,
            'measure': psutil.Process(process.pid)
        }

    async def start(self):
        """_summary_
        """
        self.task_process_manager = asyncio.Task(self._process_manager())
        self._start_process(keep=True)
        _ = [self._start_process() for _ in range(self._n - 1)]

    async def close(self) -> None:
        """_summary_
        """
        _ = [self._close_process(p_id) for p_id in self.processes]
        self.input_queue.close()
        self.output_queue.close()
        self.task_process_manager.cancel()
        with suppress(asyncio.CancelledError):
            await self.task_process_manager

    async def put(self, data):
        """_summary_

        Args:
            data (_type_): _description_
        """
        self.input_queue.put(data)
        await asyncio.sleep(0)

    async def get(self):
        """_summary_

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
