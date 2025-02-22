import schedule
import time
from loguru import logger


logger.info('Scheduler starting ...')
logger.info('Registered jobs:')
for job in schedule.get_jobs():
    logger.info(f'{job.tag()} {job.tags}')

while True:
    schedule.run_pending()
    time.sleep(1)
