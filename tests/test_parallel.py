"""Test unitarios para pprocess"""

import asyncio
import unittest
import logging
from logs.logger import CustomLogger,logger
from pprocess import TaskProcess
from pprocess.exceptions import ResponseProcessException, UserProcessException
from pprocess.utils.performance import clean_performance_data, get_performance_report
from tests.utils import TestController


CustomLogger().set_level(logging.CRITICAL + 1)
# Listado de testa a realizar:
#
# ✔️ send
# ✔️ send_bacth
# ❌ start
# ❌ close
# ❌ _requests_manager
# ❌ _repsonse_manager
# ❌ Distintas configuraciones en el __init__
# ✔️ Error en ejecución de tarea en proceso remoto
# ✔️ Cancelación de request por parte del usuario


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
            self.task_process = TaskProcess(controller=test_controller, num_processes=1)
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
        self.assertEqual(result, 20000)

    async def test_send_batch(self):
        '''Test que pruba la función send de TaskProcess
        '''
        input_data = [0, 1, 2]
        result = await self.task_process.send_batch(input_data)
        self.assertEqual(result, [0, 20000, 40000])

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
        with self.assertRaises(UserProcessException) as catch_exc:
            task.cancel()
            await task
        self.assertEqual(str(catch_exc.exception), "Se corto la ejecucion de la tarea")
        self.assertEqual(len(requests.keys()), 0)

    async def test_send_batch_requests_user_error(self):
        '''Test que pruba la función send_batch de TaskProcess y se corta la ejecución de la misma del lado de usuario
        '''

        input_data = [i for i in range(50)]
        task = asyncio.Task(self.task_process.send_batch(input_data))
        await asyncio.sleep(0.1)
        requests = self.task_process._request_storage._requests  # pylint: disable=W0212
        self.assertEqual(len(requests.keys()), 2)
        with self.assertRaises(UserProcessException) as catch_exc:
            task.cancel()
            await task
        self.assertEqual(str(catch_exc.exception), "Se corto la ejecucion de la tarea")
        self.assertEqual(len(requests.keys()), 0)
