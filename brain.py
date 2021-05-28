'''
https://realpython.com/intro-to-python-threading
'''
### packages
import os
import sys
import time
import numpy as np
import concurrent.futures
import queue
import threading

### local files


def queue_job(individual, testcase_number, output_dir, todoQ):
    sleep_time = np.random.randint(30,90)
    output_file = os.path.join(output_dir, "%s_%i.txt" % (individual, testcase_number))
    job = {'id': individual,
           'testcase': testcase_number,
           'sleep_time': sleep_time,
           'output_file': output_file}
    todoQ.put(job, block=False)


def fake_grid_engine(todoQ, fake_qsubQ):
    try:
        job = todoQ.get(block=False)
    except queue.Empty:
        # nothing to add to add to fake_qsub
        return

    try:
        fake_qsubQ.put(job, block=False)
        os.system("bash run.sh %i %s" % (job['sleep_time'], job['output_file']))
    except queue.Full:
        # can't be qsub, add back to todoQ
        todoQ.put(job, block=False)
    return


def check_if_running(fake_qsubQ, runningQ):
    try:
        job = fake_qsubQ.get(block=False)
        runningQ.put(job, block=False)
    except queue.Empty:
        return


def check_if_finished(runningQ, finishedQ):
    try:
        job = runningQ.get(block=False)
    except queue.Empty:
        return

    if os.path.exists(job['output_file']):
        finishedQ.put(job, block=False)
    else:
        runningQ.put(job, block=False)
    return


def get_scores(finishedQ, results_granular, results_aggregate):
    while True:
        try:
            job = finishedQ.get(block=False)
        except queue.Empty:
            return results_granular, results_aggregate

        with open(job['output_file'], 'r') as f:
            val = int(f.readline[:-1])

        if job['id'] in results:
            results_granular[job['id']].append(val)
        else:
            results_granular[job['id']] = [val]


        if len(results_granular[job['id']] == 50):
            # job done
            results_aggregate[job['id']] = np.array(results_granular[job['id']]).mean()
            del results_granular[job['id']]


def status_check(allQs):
    time.sleep(5)
    sizes = ()
    for Q in allQs:
        #size.append(Q.qsize())
        sizes += (Q.size,)

    print("Queue sizes: %s %s %s %s" % (sizes)); sys.stdout.flush()



if __name__ == "__main__":
    '''
    some population of individuals will exist,
    will have to evaluate each individual against a certain number of testcases.
    then collect their scores.
    '''
    POPULATION_SIZE = int(10)
    GENERATION_LIMIT = 10
    TESTCASE_COUNT = 50
    OUTPUT_DIR = "./test_number_%i" % 1
    os.makedirs(OUTPUT_DIR, exist_ok=False)

    # make queues
    todoQ = queue.Queue(maxsize=0)
    fake_qsubQ = queue.Queue(maxsize=50)
    runningQ = queue.Queue(maxsize=0)
    finishedQ = queue.Queue(maxsize=0)

    for generation in range(GENERATION_LIMIT):
        for i in range(POPULATION_SIZE):
            indiv_id = "person%i-%i" % (generation, i)
            for testcase in range(TESTCASE_COUNT):
                queue_job(individual=indiv_id,
                          testcase_number=testcase,
                          output_dir=OUTPUT_DIR,
                          todoQ=todoQ)

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            executor.submit(fake_grid_engine, todoQ, fake_qsubQ)
            executor.submit(check_if_running, fake_qsubQ, runningQ)
            executor.submit(check_if_finished, runningQ, finishedQ)
            executor.submit(status_check, [todoQ, fake_qsubQ, runningQ, finishedQ])

        results_granular = {}
        results_aggregate = {}
        still_running = True
        while still_running:
            # check finished queue
            results_granular, results_aggregate = get_scores(finishedQ, results_granular, results_aggregate)
            if len(results_aggregate) == POPULATION_SIZE:
                still_running = False
            else:
                time.sleep(5)
