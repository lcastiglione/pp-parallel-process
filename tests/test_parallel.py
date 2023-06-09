﻿"""Test unitarios para pprocess"""

import asyncio
import unittest
from pprocess import TaskProcess
from pprocess.exceptions import ResponseProcessException, ExternalProcessException
from pprocess.utils.performance import clean_performance_data, get_performance_report
from tests.utils import TestController



class TaskProcessTestCase(unittest.IsolatedAsyncioTestCase):
    '''Clase de prueba para ParallelProcess
    '''

    def __init__(self, methodName="runTest"):
        '''Inicializador de la clase EventBusTestCase.
        '''
        super().__init__(methodName=methodName)
        self.task_process = None

    async def asyncSetUp(self):
        '''Tareas asincrónas que se ejcutan antes de cada prueba.
        '''
        test_controller = TestController()
        try:
            self.task_process = TaskProcess(worker=test_controller, num_processes=1)
            await self.task_process.start()
        except Exception as exc:  # pylint: disable=W0718
            print(exc)

    async def asyncTearDown(self):
        '''Tareas asincrónas que se ejcutan después de cada prueba.
        '''
        await self.task_process.close()
        get_performance_report()
        clean_performance_data()

    async def test_send(self):
        '''Test que pruba la función send de TaskProcess
        '''
        input_data = 1
        result = await self.task_process.send(input_data)
        self.assertEqual(result, (20000,0))

    async def test_send_batch(self):
        '''Test que pruba la función send de TaskProcess
        '''
        input_data = [0, 1, 2]
        result = await self.task_process.send_batch(input_data)
        self.assertEqual(result, [[0, 20000, 40000],0])

    async def test_send_one_requests_process_error(self):
        '''Test que pruba la función send de TaskProcess y ocurre un error en el proceso
        '''
        input_data = -1
        with self.assertRaises(ResponseProcessException) as catch_exc:
            await self.task_process.send(input_data)
        self.assertEqual(str(catch_exc.exception), "Se produjo un error al procesar la tarea: Simulando error desde un proceso")

    async def test_send_multiple_requests_process_error(self):
        '''Test que pruba la función send de TaskProcess y ocurre un error en el proceso
        '''
        input_data = -1
        with self.assertRaises(ResponseProcessException) as catch_exc:
            tasks = [self.task_process.send(input_data) for _ in range(10)]
            await asyncio.gather(*tasks)
        self.assertEqual(str(catch_exc.exception), "Se produjo un error al procesar la tarea: Simulando error desde un proceso")

    async def test_send_batch_requests_process_error(self):
        '''Test que pruba la función send_batch de TaskProcess y ocurre un error en el proceso
        '''
        input_data = [-1, 0, 1]
        with self.assertRaises(ResponseProcessException) as catch_exc:
            await self.task_process.send_batch(input_data)
        self.assertEqual(str(catch_exc.exception), "Se produjo un error al procesar la tarea: Simulando error desde un proceso")

    async def test_send_one_requests_user_error(self):
        '''Test que pruba la función send de TaskProcess y se corta la ejecución de la misma del lado de usuario
        '''
        input_data = 2
        task = asyncio.Task(self.task_process.send(input_data))
        await asyncio.sleep(0.1)
        requests = self.task_process._request_storage._requests  # pylint: disable=W0212
        self.assertEqual(len(requests.keys()), 1)
        with self.assertRaises(ExternalProcessException) as catch_exc:
            task.cancel()
            await task
        self.assertEqual(str(catch_exc.exception), "Un suceso externo corto la ejecucion del procesador de tareas")
        self.assertEqual(len(requests.keys()), 0)

    async def test_send_batch_requests_user_error(self):
        '''Test que pruba la función send_batch de TaskProcess y se corta la ejecución de la misma del lado de usuario
        '''
        input_data = [i for i in range(50)]
        task = asyncio.Task(self.task_process.send_batch(input_data))
        await asyncio.sleep(0.1)
        requests = self.task_process._request_storage._requests  # pylint: disable=W0212
        self.assertEqual(len(requests.keys()), 2)
        with self.assertRaises(ExternalProcessException) as catch_exc:
            task.cancel()
            await task
        self.assertEqual(str(catch_exc.exception), "Un suceso externo corto la ejecucion del procesador de tareas")
        self.assertEqual(len(requests.keys()), 0)

    """ async def test_cpu(self):
        '''Test para probar el controlador de procesos para la creación y cierre de procesos autónoma según el consumo de CPU. Activar el test solo cuando se pruebe esto.
        '''
        asyncio.Task(self.task_process.send(-2))
        await asyncio.sleep(20) """
