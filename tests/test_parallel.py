"""Test unitarios para pprocess"""
import asyncio
import time
import unittest

from pprocess.pprocess import ParallelProcess
from pprocess.utils import find_small_missing_number
from tests.utils import TestController, method
from datetime import datetime


size=10
num_processes=10

class ParallelProcessTestCase(unittest.IsolatedAsyncioTestCase):
    '''Clase de prueba para ParallelProcess
    '''

    def __init__(self, methodName="runTest"):
        '''Inicializador de la clase EventBusTestCase.
        '''
        super().__init__(methodName=methodName)
        self.p_process = None

    async def asyncSetUp(self):
        '''Tareas asincrónas que se ejcutan antes de cada prueba.
        '''
        test_controller = TestController()
        try:
            self.p_process = ParallelProcess(controller=test_controller, num_processes=num_processes,chunk_requests=int(size/num_processes))
            await self.p_process.start()
        except Exception as exc:
            print(exc)
        self.loop=asyncio.get_event_loop()
        self.loop.set_debug(False)

    async def asyncTearDown(self):
        '''Tareas asincrónas que se ejcutan después de cada prueba.
        '''
        await self.p_process.close()
        asyncio.all_tasks(self.loop)

    async def test_start(self):
        """_summary_
        """
        print("Ejecutar test")
        batch=[i for i in range(size)]
        for i in range(2):
            start_t=time.time_ns()
            await self.p_process.exe_task(batch)
            print(f"Tiempo de ejecución: {round((time.time_ns()-start_t)/1000000,2)}ms")

        start_t=time.time_ns()
        [method(i)for i in batch]
        print(f"Tiempo de ejecución original: {round((time.time_ns()-start_t)/1000000,2)}ms")

        #print(results)
        #await asyncio.sleep(100)
