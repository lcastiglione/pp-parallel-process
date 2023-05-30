"""_summary_"""
from multiprocessing.connection import PipeConnection
import traceback
import queue
import time
from typing import Any


TIME_WAIT: int = 60  # 1 min


class Controller:
    """_summary_"""

    @classmethod
    def worker(cls, process_id: int, conn: PipeConnection, keep: bool = False) -> None:
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
                r_id, input_data = conn.recv()
                print(f"Recibo a: {r_id}")
                results: Any = cls.execute(input_data)
                #time.sleep(20)
                conn.send((r_id, results))
                print(f"Responder a: {r_id}")
                start_time = time.time()
            except queue.Empty:
                pass
            except KeyboardInterrupt:
                break
            except Exception as exc:
                traceback.print_exc()
                conn.send((r_id, exec))
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
