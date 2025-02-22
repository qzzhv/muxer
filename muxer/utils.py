import luigi


def luigi_runner(*tasks):
    def luigi_task():
        return luigi.build(tasks)
    return luigi_task


def add_luigi_task(timing, task):
    return timing.do(luigi_runner(task)).tag(task.task_family, task.task_module, f'{task}')
