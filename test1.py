from multiprocessing import Process, Pipe
import time

def reader_proc(pipe):
    ## Read from the pipe; this will be spawned as a separate Process
    p_output, p_input = pipe
    p_input.close()    # We are only reading
    while True:
        msg = p_output.recv()    # Read from the output pipe and do nothing
        print(msg)
        if msg=='DONE':
            break

def writer(p_input):
    msg = {'test': 1234}
    p_input.send(msg)             # Write 'count' numbers into the input pipe
    p_input.send('DONE')

if __name__=='__main__':
    
    # Pipes are unidirectional with two endpoints:  p_input ------> p_output
    p_output, p_input = Pipe()  # writer() writes to p_input from _this_ process
    reader_p = Process(target=reader_proc, args=((p_output, p_input),))
    reader_p.daemon = True
    reader_p.start()     # Launch the reader process

    p_output.close()       # We no longer need this part of the Pipe()
    _start = time.time()
    writer(p_input) # Send a lot of stuff to reader_proc()
    p_input.close()
    reader_p.join()
    print("Sending {0} numbers to Pipe() took {1} seconds".format(1,
        (time.time() - _start)))