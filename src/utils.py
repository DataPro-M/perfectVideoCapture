import os
import redis

'''
write the pid file
'''
def write_pid_file(pid_file):
    with open(pid_file, 'w') as f:
        f.write(str(os.getpid()))

'''
connect to redis server
'''
def connect_redis(redis_host, redis_port):
    return redis.Redis(host=redis_host, port=redis_port, db=0)