# main.py
from fastapi import FastAPI
from logs.logger import logger
from pprocess import TaskProcess
from pprocess.exceptions import ResponseProcessException
from app.controller import CustomController

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    controller = CustomController()
    app.task_process = TaskProcess(worker=controller,
                                   num_processes=2,
                                   max_num_process=4,
                                   chunk_requests=30,
                                   time_chunk_requests=10)  # En ms
    await app.task_process.start()

@app.on_event("shutdown")
async def shutdown_event():
    await app.task_process.close()

@app.get("/log")
async def log_endpoint():
    logger.error("test")
    return {"message": "ok"}


@app.get("/parallel")
async def parallel_process():
    input_data = 3
    try:
        result = await app.task_process.send(input_data)
        return {"message":result}
    except ResponseProcessException as exc:
        print(exc)

