"""Test unitarios para pprocess"""
import unittest

from pprocess.pprocess import ParallelProcess
from tests.utils import TestController

def method(value):
    return value*3
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
        self.p_process = ParallelProcess(controller=test_controller)
        await self.p_process.start()

    async def asyncTearDown(self):
        '''Tareas asincrónas que se ejcutan después de cada prueba.
        '''
        await self.p_process.close()

    async def test_start(self):
        """_summary_
        """


        result = await self.p_process.exe_task({'method': method, 'input': 3})
        print("termine la tarea")
        print(result)
