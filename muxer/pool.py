import datetime as dt
import time
from dataclasses import dataclass

import luigi
import pycron
from loguru import logger


@dataclass
class PoolTask:
    task: luigi.Task
    cron: str


class Pool:
    pool: list[PoolTask] = []
    wait_from: dict[PoolTask, dt.datetime] = {}

    @classmethod
    def add_task(cls, task: luigi.Task, cron: str):
        cls.pool.append(PoolTask(task=task, cron=cron))
        logger.info(f'added task {task}')

    @classmethod
    def need_to_run(cls, pool_task: PoolTask):
        last_run = cls.wait_from.get(pool_task.__repr__())

        if last_run is None:
            cls.wait_from[pool_task.__repr__()] = dt.datetime.now()
            return pycron.is_now(pool_task.cron)
        elif last_run + dt.timedelta(minutes=1) > dt.datetime.now():
            return False
        else:
            return pycron.has_been(
                pool_task.cron,
                since=last_run + dt.timedelta(minutes=1),
            )

    @classmethod
    def run_task(cls, pool_task: PoolTask):
        cls.wait_from[pool_task.__repr__()] = dt.datetime.now()
        luigi.build([pool_task.task])

    @classmethod
    def run(cls):
        logger.info('start pool')
        while True:
            for pool_task in cls.pool:
                try:
                    if cls.need_to_run(pool_task):
                        logger.info(f'start {pool_task}')
                        cls.run_task(pool_task)

                except luigi.RPCError:
                    raise
                except Exception as e:
                    logger.error(e)

            time.sleep(5)
