'''
https://realpython.com/intro-to-python-threading
'''
### packages
import os
import sys
import time
import numpy as np
import concurrent.futures
import subprocess
import queue
import threading
import logging

### local files


def queue_job(individual, testcase_number, output_dir, todoQ):
    logging.debug("Add to ToDo - Start - %s for __sec" % (individual))
    sleep_time = np.random.randint(30,90)
    output_file = os.path.join(output_dir, "%s_%i.txt" % (individual, testcase_number))
    job = {'id': individual,
           'testcase': testcase_number,
           'sleep_time': sleep_time,
           'output_file': output_file}
    logging.debug("Add to ToDo - Middle - %s assigned for %isec" % (individual, sleep_time))
    todoQ.put(job, block=False)
    logging.info("Add to ToDo - Done - Success %s" % (individual))


def fake_grid_engine(event, todoQ, fake_qsubQ):
    while not event.is_set():
        #time.sleep(1)
        logging.debug("Add to Grid - Start")
        try:
            job = todoQ.get(block=False)
        except queue.Empty:
            # nothing to add to add to fake_qsub
            logging.info("Add to Grid - Done - ToDo empty")
            continue

        logging.debug("Add to Grid - Middle - %s" % job['id'])
        try:
            fake_qsubQ.put(job, block=False)
            cmd = "bash run.sh %i %s" % (job['sleep_time'], job['output_file'])
            #os.system(cmd)
            subprocess.Popen(cmd.split(" "))#, creationflags=subprocess.CREATE_NEW_CONSOLE)
            logging.info("Add to Grid - Done - %s Success" % job['id'])
        except queue.Full:
            # can't be qsub, add back to todoQ
            todoQ.put(job, block=False)
            logging.info("Add to Grid - Done - %s Grid full" % job['id'])


def check_if_running(event, fake_qsubQ, runningQ):
    while not event.is_set():
        #time.sleep(1)
        logging.debug("Add to Running - Start")
        try:
            job = fake_qsubQ.get(block=False)
        except queue.Empty:
            logging.info("Add to Running - Done - Grid empty")
            continue

        logging.debug("Add to Running - Middle - %s" % job['id'])
        runningQ.put(job, block=False)
        logging.info("Add to Running - Done - Success - %s" % job['id'])


def check_if_finished(event, runningQ, finishedQ):
    while not event.is_set():
        #time.sleep(1)
        logging.debug("Add to Finished - Start")
        try:
            job = runningQ.get(block=False)
        except queue.Empty:
            logging.info("Add to Finished - Done - Running empty")
            continue

        logging.debug("Add to Finished - Middle - %s" % job['id'])
        if os.path.exists(job['output_file']):
            finishedQ.put(job, block=False)
            logging.info("Add to Finished - Done - %s finished" % job['id'])
        else:
            runningQ.put(job, block=False)
            logging.info("Add to Finished - Done - %s still running" % job['id'])


def get_scores2(finishedQ, results_granular, results_aggregate):
    logging.debug("Main Loop - Get Scores - Start")
    while True:
        try:
            job = finishedQ.get(block=False)
        except queue.Empty:
            logging.info("Main Loop - Get Scores - Done - Finished empty")
            return results_granular, results_aggregate

        return np.ones((10,)), np.ones((10,))


def get_scores(finishedQ, results_granular, results_aggregate):
    logging.debug("Main Loop - Get Scores - Start")
    while True:
        try:
            job = finishedQ.get(block=False)
        except queue.Empty:
            logging.info("Main Loop - Get Scores - Done - Finished empty")
            return results_granular, results_aggregate
			
        with open(job['output_file'], 'r') as f:
            val = int(f.readline()[:-1])
        logging.debug("Main Loop - Get Scores - %s scored %i" % (job['id'], val))

        if job['id'] in results_granular:
            results_granular[job['id']].append(val)
        else:
            results_granular[job['id']] = [val]
        logging.debug("Main Loop - Get Scores - %s scored recorded" % (job['id']))


        if len(results_granular[job['id']]) == 50:
            # job done
            results_aggregate[job['id']] = np.array(results_granular[job['id']]).mean()
            del results_granular[job['id']]
            logging.debug("Main Loop - Get Scores - %s scored against ALL to %.2f" % (job['id'], results_aggregate[job['id']]))

        logging.info("Main Loop - Get Scores - Done - %s" % job['id'])


def status_check(allQs):
    #logging.debug("Status Check - Sleep")
    #time.sleep(5)
    logging.debug("Status Check - Start")
    sizes = ()
    for Q in allQs:
        #size.append(Q.qsize())
        sizes += (Q.qsize(),)

    logging.debug("Status Check -  %s %s %s %s" % (sizes))
    print("Queue sizes: %s %s %s %s" % (sizes)); sys.stdout.flush()


def main_loop(event, allQs):
    logging.debug("Main Loop - Start")
    results_granular = {}
    results_aggregate = {}
    still_running = True
    while still_running:
        logging.debug("Main Loop - While loop")
        # check finished queue
        status_check(allQs)
        results_granular, results_aggregate = get_scores(allQs[-1], results_granular, results_aggregate)
        if len(results_aggregate) == POPULATION_SIZE:
            still_running = False
			event.set()
            logging.info("Main Loop - Terminating!")
        else:
            logging.debug("Main Loop - Sleep")
            time.sleep(5)

    return results_aggregate


if __name__ == "__main__":
    '''
    some population of individuals will exist,
    will have to evaluate each individual against a certain number of testcases.
    then collect their scores.
    '''
    POPULATION_SIZE = int(10)
    GENERATION_LIMIT = 5
    TESTCASE_COUNT = 50
    OUTPUT_DIR = "./test_number_%i" % 0
    os.makedirs(OUTPUT_DIR, exist_ok=False)

    # make queues
    todoQ = queue.Queue(maxsize=0)
    fake_qsubQ = queue.Queue(maxsize=50)
    runningQ = queue.Queue(maxsize=0)
    finishedQ = queue.Queue(maxsize=0)

    logging.basicConfig(format="%(asctime)s: %(message)s",
                        level=logging.DEBUG,
                        datefmt="%H:%M:%S")

    rootLogger = logging.getLogger()

    fileHandler = logging.FileHandler(os.path.join(OUTPUT_DIR, "file.log"))
    rootLogger.addHandler(fileHandler)


    for generation in range(GENERATION_LIMIT):
        event = threading.Event()
        logging.warning("\nMain Loop - Starting Next Generation - %i" % generation)

        for i in range(POPULATION_SIZE):
            indiv_id = "person%i-%i" % (generation, i)
            for testcase in range(TESTCASE_COUNT):
                queue_job(individual=indiv_id,
                          testcase_number=testcase,
                          output_dir=OUTPUT_DIR,
                          todoQ=todoQ)

        logging.warning("Main Loop - Population Sent to Eval")
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            executor.submit(fake_grid_engine, event, todoQ, fake_qsubQ)
            executor.submit(check_if_running, event, fake_qsubQ, runningQ)
            executor.submit(check_if_finished, event, runningQ, finishedQ)
            future = executor.submit(main_loop, event, [todoQ, fake_qsubQ, runningQ, finishedQ]) #https://docs.python.org/3/library/concurrent.futures.html#concurrent.futures.Executor.submit

        results_aggregate = future.result()
        logging.info("FINAL RESULTS: %s" % results_aggregate)
