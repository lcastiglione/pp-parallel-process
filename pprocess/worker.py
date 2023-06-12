"""Módulo encargado de definir las funciones del worker quetrabaj en un proceso separado"""

import queue
import time
from typing import Any
from abc import ABC, abstractmethod

TIME_WAIT: int = 60*30  # 30 min


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
        cls.start_process(process_id)
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
                # Cuando se cumple el timeout sin recibir mensaje, se lanza una excepción de queue vacío.
                # Se captura, se ignora y se sigue esperando
                pass
            except KeyboardInterrupt:
                break
            except Exception as exc:  # pylint: disable=W0718
                # Todos los posibles errores que puedan ocurrir en el proceso, deberían estar cubiertos
                # por la implementación del worker. Si un error no es tenido en cuenta, se captura acá y se
                # los cataloga como crítico.
                cls.print_error("Hubo un error inesperado en el proceso", process_id=process_id, exc=exc)
                try:
                    o_queue.put((process_id, r_ids, None, [str(exc)]*len(r_ids)))
                except Exception as exc_queue:  # pylint: disable=W0718
                    cls.print_error("Fallo el envio de datos por el output queue", process_id=process_id, exc=exc_queue)
                    break
        cls.stop_process(process_id)

    @classmethod
    def print_error(cls, error_message: str, process_id: int = None, exc: Exception = None) -> None:
        """Método para procesar errores inesperados dentro del proceso. Cada implementación de
        pprocess deberá definir este método pero por default, se muestra en consola.
        """
        print(f"Mensaje de error: {error_message}. ID del proceso: {process_id}. Error: {str(exc)}")

    @classmethod
    @abstractmethod
    def start_process(cls, process_id: int) -> None:
        """Método abstracto que se ejecuta cuando se abre un nuevo proceso
        """

    @classmethod
    @abstractmethod
    def stop_process(cls, process_id: int) -> None:
        """Método abstracto que se ejecuta cuando se cierra un proceso
        """

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
