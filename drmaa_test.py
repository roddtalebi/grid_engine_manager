'''
quick file for testing drmaa stuff

going to follow the examples in the drmaa tutorial
https://drmaa-python.readthedocs.io/en/latest/tutorials.html
'''
import os
import sys
import time
import drmaa


with drmaa.Session() as s:
    jt = s.createJobTemplate()
    jt.remoteCommand = os.path.join(os.getcwd(), 'run_simple.sh')
    jt.args = []
    jt.joinFiles = True
    #jt.nativeSpecification = "-q all" # CHANGE QUEUE NAME
    jobid = s.runJob(jt)
    print('Your job has been submitted with ID %s' % jobid)

    #start = time.time()
    for _ in range(120):
        time.sleep(0.5)
        print('\tChecking status -> %s' % (s.jobStatus(jobid)))

    print('Cleaning up')
    s.deleteJobTemplate(jt)

print("Did job succeed?")
if os.path.exists("simple_test.txt"):
    print("\tSUCCESS!")
else:
    print("\tFAILED.")

print("") #empty line to close