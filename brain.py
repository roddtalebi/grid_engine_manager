'''
https://realpython.com/intro-to-python-threading

note, for searching through queues, i recommend doing this method from 
https://stackoverflow.com/questions/16686292/examining-items-in-a-python-queue
myQ = queue.Queue()
for job in my_jobs:
    myQ.put(job)

snapshot_queue = list(myQ.queue)

that should provide you with a copy of the underlying queue that is iterable instead of using myQ.queue directly which would be 'live'
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
import drmaa

### local files


def frozen_snapshot_queue(my_queue):
    '''
    https://stackoverflow.com/questions/16686292/examining-items-in-a-python-queue
    the queue.Queue object has a queue attribute which is a deque which can be iterated over,
    BUT using the deque will keep it as a 'live' version which can change as you iterate over it.
    Convert it to a list to freeze the copy.
    '''
    return list(my_queue.queue)


def react_job_status(drmaa_session,
                     job,
                     todoQ=None,
                     runningQ=None,
                     finishedQ=None):
    job_status = drmaa_session.jobStatus(job['jobid'])

    if job_status in [drmaa.JobState.UNDETERMINED,
                      drmaa.JobState.QUEUED_ACTIVE,
                      drmaa.JobState.SYSTEM_ON_HOLD,
                      drmaa.JobState.USER_ON_HOLD,
                      drmaa.JobState.USER_SYSTEM_ON_HOLD]:
        # add back to todoQ
        todoQ.put(job, block=False)

    elif job_status in [drmaa.JobState.RUNNING]:
        runningQ.put(job, block=False)

    elif job_status in [drmaa.JobState.SYSTEM_SUSPENDED,
                        drmaa.JobState.USER_SUSPENDED,
                        drmaa.JobState.DONE,
                        drmaa.JobState.FAILED]:
        finishedQ.put(job, block=False)

    else:
        logging.critical("UH WHOT? Got this unexpected job status %s" % (str(job_status)))



def queue_job(individual, testcase_number, output_dir, todoQ, drmaa_session):
    logging.debug("Add to ToDo - Start - %s for __sec" % (individual))
    sleep_time = np.random.randint(30,90)
    output_file = os.path.join(os.getcwd(), output_dir, "%s_%i.txt" % (individual, testcase_number))

    # https://drmaa-python.readthedocs.io/en/latest/tutorials.html#running-a-job
    jt = drmaa_session.createJobTemplate()
    jt.remoteCommand = os.path.join(os.getcwd(), 'run.sh')
    jt.args = [sleep_time, output_file]
    jt.joinFiles = True
    jobid = drmaa_session.runJob(jt) 

    job = {'id': individual,
           'testcase': testcase_number,
           'sleep_time': sleep_time,
           'output_file': output_file,
           'jobid': jobid}
    logging.debug("Add to ToDo - Middle - %s assigned for %isec" % (individual, sleep_time))
    todoQ.put(job, block=False)
    logging.info("Add to ToDo - Done - Success %s" % (individual))


def check_if_running(event, drmaa_session, todoQ, runningQ, finishedQ):
    try:
        while not event.is_set():
            logging.debug("Add to Running - Start")
            try:
                job = todoQ.get(block=False)
            except queue.Empty:
                logging.info("Add to Running - Done - todoQ empty")
                continue

            logging.debug("Add to Running - Middle - %s" % job['id'])
            react_job_status(drmaa_session, job, todoQ, runningQ, finishedQ)
            logging.info("Add to Running - Done - %s" % job['id'])
    except Exception as e:
        logging.critical("'check_if_running' Thread Failed - %s" % e)
        event.set()


def check_if_finished(event, todoQ, runningQ, finishedQ):
    try:
        while not event.is_set():
            logging.debug("Add to Finished - Start")
            try:
                job = runningQ.get(block=False)
            except queue.Empty:
                logging.info("Add to Finished - Done - Running empty")
                continue

            logging.debug("Add to Finished - Middle - %s" % job['id'])
            react_job_status(drmaa_session, job, todoQ, runningQ, finishedQ)
            logging.info("Add to Finished - Done - %s" % job['id'])
    except Exception as e:
        logging.critical("'check_if_finished' Thread Failed - %s" % e)
        event.set()


def get_scores(drmaa_session, finishedQ, results_granular, results_aggregate):
    logging.debug("Main Loop - Get Scores - Start")
    while True:
        try:
            job = finishedQ.get(block=False)
        except queue.Empty:
            logging.info("Main Loop - Get Scores - Done - Finished empty")
            return results_granular, results_aggregate


        job_status = drmaa_session.jobStatus(job['jobid'])
        if job_status in drmaa.JobState.DONE:
            # finished normally!
            with open(job['output_file'], 'r') as f:
                val = int(f.readline()[:-1])
            logging.debug("Main Loop - Get Scores - %s scored %i" % (job['id'], val))
        else:
            # must have failed
            val = None

        if job['id'] in results_granular:
            results_granular[job['id']].append(val)
        else:
            results_granular[job['id']] = [val]
        logging.debug("Main Loop - Get Scores - %s scored recorded" % (job['id']))


        if len(results_granular[job['id']]) == TESTCASE_COUNT:
            # job done
            results_np = np.array(results_granular[job['id']])
            failed_count = len(results_np[results_np==None])
            results_np = results_np[results_np!=None]
            results_aggregate[job['id']] = results_np.mean()
            del results_granular[job['id']]
            logging.debug("Main Loop - Get Scores - %s scored against ALL to %.2f - %i failed" % (job['id'], results_aggregate[job['id']], failed_count))

        logging.info("Main Loop - Get Scores - Done - %s" % job['id'])


def status_check(allQs):
    #logging.debug("Status Check - Sleep")
    #time.sleep(5)
    logging.debug("Status Check - Start")
    sizes = ()
    for Q in allQs:
        #size.append(Q.qsize())
        sizes += (Q.qsize(),)

    logging.debug("Status Check -  %s %s %s" % (sizes))
    print("Queue sizes: %s %s %s" % (sizes)); sys.stdout.flush()


def main_loop(event, drmaa_session, todoQ, runningQ, finishedQ):
    results_granular = {}
    results_aggregate = {}
    try:
        logging.debug("Main Loop - Start")
        while not event.is_set():
            logging.debug("Main Loop - While loop")
            # check finished queue
            status_check([todoQ, runningQ, finishedQ])
            results_granular, results_aggregate = get_scores(drmaa_session, finishedQ, results_granular, results_aggregate)
            if len(results_aggregate) == POPULATION_SIZE:
                event.set()
                logging.info("Main Loop - Terminating!")
            else:
                logging.debug("Main Loop - Sleep")
                time.sleep(5)
    except Exception as e:
        logging.critical("'main_loop' Thread Failed - %s" % e)
        event.set()

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
    runningQ = queue.Queue(maxsize=0)
    finishedQ = queue.Queue(maxsize=0)

    logging.basicConfig(format="%(asctime)s: %(message)s",
                        level=logging.DEBUG,
                        datefmt="%H:%M:%S")
    rootLogger = logging.getLogger()
    fileHandler = logging.FileHandler(os.path.join(OUTPUT_DIR, "file.log"))
    rootLogger.addHandler(fileHandler)

    session = drmaa.Session()
    session.initialize()
    response = session.contact

    for generation in range(GENERATION_LIMIT):
        event = threading.Event()
        logging.warning("\nMain Loop - Starting Next Generation - %i" % generation)

        for i in range(POPULATION_SIZE):
            indiv_id = "person%i-%i" % (generation, i)
            for testcase in range(TESTCASE_COUNT):
                queue_job(individual=indiv_id,
                          testcase_number=testcase,
                          output_dir=OUTPUT_DIR,
                          todoQ=todoQ,
                          drmaa_session=session)

        logging.warning("Main Loop - Population Sent to Eval")
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            executor.submit(check_if_running, event, session, todoQ, runningQ, finishedQ)
            executor.submit(check_if_finished, event, session, todoQ, runningQ, finishedQ)
            future = executor.submit(main_loop, event, session, todoQ, runningQ, finishedQ) #https://docs.python.org/3/library/concurrent.futures.html#concurrent.futures.Executor.submit

        results_aggregate = future.result()
        logging.info("FINAL RESULTS: %s" % results_aggregate)
        break
    session.exit()