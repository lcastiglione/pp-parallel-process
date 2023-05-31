"""_summary_"""
import queue
import time
import traceback
from typing import Any

TIME_WAIT: int = 60  # 1 min


class Controller:
    """_summary_"""

    @classmethod
    def worker(cls, process_id: int, i_queue, o_queue, keep: bool = False) -> None:
        """_summary_

        Args:
            input_queue (queue.Queue): Objeto Queue para recibir parámetros a procesar desde el hilo principal
            output_queue (queue.Queue): Objeto Queue para enviar respuesta al hilo principal
            keep (bool, optional): Indica si el proceso se tiene que mantener vivo si o sí. Por default es False
        """
        # print(f"Se abre proceso {process_id}")
        cls.load_config()
        unused_process_time = time.time()
        while True and ((time.time() - unused_process_time) < TIME_WAIT or keep):
            try:
                r_id, input_data,index = i_queue.get(timeout=0.001)
                results: Any = cls.execute(input_data)
                #time.sleep(20)
                o_queue.put((process_id, r_id, results,index))
                unused_process_time = time.time()
            except queue.Empty:
                pass
            except KeyboardInterrupt:
                break
            except Exception as exc:  # pylint: disable=W0718
                traceback.print_exc()
                o_queue.put((process_id, r_id, exc))
        # print(f"Se cierra proceso {process_id}")

    @classmethod
    def load_config(cls) -> None:
        """_summary_"""

    @classmethod
    def execute(cls, params: Any) -> Any:
        """_summary_

        Args:
            params (Any): _description_
        """
