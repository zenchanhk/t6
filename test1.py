from multiprocessing import Process, Pipe
import time
msg = {}
def reader_proc(pipe):
    ## Read from the pipe; this will be spawned as a separate Process
    p_output, p_input = pipe
    p_input.close()    # We are only reading
    msg = {}
    while True:
        d = p_output.recv()
        print(d)
        msg.update(d)    # Read from the output pipe and do nothing
        #print(msg)
        if d=='w1':
            print('after w1')
            print(len(msg))
        if d=='DONE':
            print('after w2')
            print(len(msg))
            #break

def writer(p_input):
    for i in range(1000):
        msg1 = {'testa'+str(i): 1234+i}
        p_input.send(msg1)             # Write 'count' numbers into the input pipe
    p_input.send('w1')

def writer1(p_input):
    for i in range(100):
        msg1 = {'testb'+str(i): 123456+i}
        p_input.send(msg1)             # Write 'count' numbers into the input pipe
    p_input.send('DONE')

def test(msg):    
    msg.update({'23': 34})
    print(msg)

def test1(msg):    
    msg.update({'test': 325})
    print(msg)

class ab(dict):
    pass

if __name__=='__main__':
    
    # Pipes are unidirectional with two endpoints:  p_input ------> p_output
    p_output, p_input = Pipe()  # writer() writes to p_input from _this_ process
    reader_p = Process(target=reader_proc, args=((p_output, p_input),))
    reader_p.daemon = True
    reader_p.start()     # Launch the reader process

    p_output.close()       # We no longer need this part of the Pipe()
    _start = time.time()
    # writer(p_input) # Send a lot of stuff to reader_proc()
    #w_p1 = Process(target=writer, args=((p_input),))
    #w_p = Process(target=writer1, args=((p_input),))
    #w_p1.start()
    #w_p.start()
    #w_p1.join()
    #w_p.join()
    msg = ab()
    w_t1 = Process(target=test, args=((msg),))
    w_t = Process(target=test1, args=((msg),))
    #reader_p.join()
    #p_input.close()
    w_t.start()
    w_t1.start()
    w_t.join()
    w_t1.join()
    print(msg)
    print("Sending {0} numbers to Pipe() took {1} seconds".format(1,
        (time.time() - _start)))
    