"""_summary_"""
import traceback
import queue
import time
from typing import Any


TIME_WAIT: int = 60 * 60 * 1000  # 1 min


class Controller:
    """_summary_"""

    @classmethod
    def worker(cls, input_queue: queue.Queue, output_queue: queue.Queue, keep: bool = False) -> None:
        """_summary_

        Args:
            input_queue (queue.Queue): _description_
            output_queue (queue.Queue): _description_
            keep (bool, optional): _description_. Defaults to False.
        """
        count: int = 0
        cls.load_config()
        while True and (count < TIME_WAIT or keep):
            try:
                params: Any = input_queue.get_nowait()
                count = 0
                # log(f"Se procesan {len(params)} peticiones en el proceso {process_id}")
                results: Any = cls.execute(params)
                output_queue.put(results)
            except KeyboardInterrupt as exc:
                #print(exc)
                # log(f"Error en el proceso {process_id}: {exc}", LOG_LEVEL.ERROR)
                break
            except queue.Empty as exc:
                #print(exc)
                count += 1
            except Exception as exc:  # pylint: disable=W0718
                # Sirve para capturar errores inesperados y no romper el proceso
                # log(exc, LOG_LEVEL.ERROR)
                traceback.print_exc()
                output_queue.put([exc] * len(params))
            try:
                time.sleep(0.001)
            except KeyboardInterrupt as exc:
                #print(exc)
                break
        if count >= TIME_WAIT:
            # log(f"Se cierra automáticamente el proceso {process_id}")
            pass

    @classmethod
    def load_config(cls) -> None:
        """_summary_"""

    @classmethod
    def execute(cls, params: Any) -> Any:
        """_summary_

        Args:
            params (Any): _description_
        """
