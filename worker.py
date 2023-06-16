import requests
import time
import sys 

parent_ip = sys.arg[1]
other_ip = sys.arg[2]
cur_ip = parent_ip

def get_work_to_do():
    try:
        cur_ip = parent_ip
        work_item = requests.get(f'http://{parent_ip}:5000/get_next_work')       
    except:
        return '', 400
        
    if work_item.status_code != 200:
        try:
            cur_ip = other_ip
            work_item = requests.get(f'http://{other_ip}:5000/get_next_work')
        except:
            return '', 400
        if work_item.status_code != 200:
            return '', 404 
    return work_item 

def worker():
    while True:
        work_to_do = get_work_to_do()
        if work.status_code != 200:
            time.sleep(10)
            continue 
        work_to_do = work_to_do['work']
        if work_to_do is None:
            time.sleep(10)
            continue
        res = work(work_to_do['data'], work_to_do['iterations'])
        requests.post(f'http://{cur_ip}:5000/completed_work', data={'work_id': work_to_do['work_id'], 'result': res})


def work(buffer, iterations):
    import hashlib
    output = hashlib.sha512(buffer).digest()
    for i in range(iterations - 1):
        output = hashlib.sha512(output).digest()
    return output

worker()