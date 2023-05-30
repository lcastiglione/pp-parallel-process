"""_summary_"""
import traceback
import queue
import time
from typing import Any


TIME_WAIT: int = 60  # 1 min


class Controller:
    """_summary_"""

    @classmethod
    def worker(cls, process_id:int,input_queue: queue.Queue, output_queue: queue.Queue, keep: bool = False) -> None:
        """_summary_

        Args:
            input_queue (queue.Queue): Objeto Queue para recibir parámetros a procesar desde el hilo principal
            output_queue (queue.Queue): Objeto Queue para enviar respuesta al hilo principal
            keep (bool, optional): Indica si el proceso se tiene que mantener vivo si o sí. Por default es False
        """
        #print(f"Se abre proceso {process_id}")
        cls.load_config()
        start_time = time.time()
        while True and ((time.time() - start_time) < TIME_WAIT or keep):
            try:
                params: Any = input_queue.get(timeout=0.001)
                results: Any = cls.execute(params)
                output_queue.put(results)
                start_time = time.time()
            except queue.Empty:
                pass
            except KeyboardInterrupt:
                break
            except Exception as exc:
                traceback.print_exc()
                output_queue.put([exc] * len(params))
        #print(f"Se cierra proceso {process_id}")

    @classmethod
    def load_config(cls) -> None:
        """_summary_"""

    @classmethod
    def execute(cls, params: Any) -> Any:
        """_summary_

        Args:
            params (Any): _description_
        """
