import schedule
import time

from .tasks import TASKS


for table, job in TASKS:
    table.do(job)

while True:
    schedule.run_pending()
    time.sleep(1)
