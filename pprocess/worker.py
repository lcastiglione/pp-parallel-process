"""Módulo encargado de definir las funciones del worker quetrabaj en un proceso separado"""

import queue
import time
from typing import Any
from abc import ABC, abstractmethod
from logs.logger import logger

TIME_WAIT: int = 1800  # 30 min

class Worker(ABC):
    """Clase abstracta que define las funciones para generar un trabajor en otro proceso.
    """

    @classmethod
    def loop(cls, process_id: int, i_queue, o_queue, keep: bool = False) -> None:
        """Función que ejecuta un loop eterno esperando a que lleguen peticiones y devolviendo datos procesados.

        Args:
            input_queue (queue.Queue): Objeto Queue para recibir parámetros a procesar desde el hilo principal
            output_queue (queue.Queue): Objeto Queue para enviar respuesta al hilo principal
            keep (bool, optional): Indica si el proceso se tiene que mantener vivo si o sí. Por default es False
        """
        cls.load_config()
        unused_process_time = time.time()
        while True and ((time.time() - unused_process_time) < TIME_WAIT or keep):
            try:
                params = i_queue.get(timeout=0.001)
                r_ids, inputs_data = zip(*params)
                results, errors = cls.execute(inputs_data)
                o_queue.put((process_id, r_ids, results, errors))
                unused_process_time = time.time()
            except queue.Empty:
                pass
            except KeyboardInterrupt:
                break
            except Exception as exc:  # pylint: disable=W0718
                logger.critical("Hubo un error inesperado en el proceso %i: %s", process_id, str(exc), exc_info=True)
                o_queue.put((process_id, r_ids, None, [str(exc)]*len(r_ids)))

    @classmethod
    @abstractmethod
    def load_config(cls) -> None:
        """Método abstracto para cargar variables o jecutar funciones previo a la ejecuión de execute.
        """

    @classmethod
    @abstractmethod
    def execute(cls, params: Any) -> Any:
        """Método abstracto para ejecutar código pesado en otro proceso

        Args:
            params (Any): Parámetros necesarios para ejecutar la función.
        """
