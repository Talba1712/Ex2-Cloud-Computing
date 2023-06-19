import requests
import time
import sys 

parent_ip = sys.argv[1]
other_ip = sys.argv[2]
cur_ip = parent_ip

def get_work_to_do():
    try:
        cur_ip = parent_ip
        work_item = requests.get(f'http://{parent_ip}:5000/get_next_work')
        status_code = int (work_item.status_code)
    except:
        return {"status_code":400}
    if status_code != 200:
        try:
            cur_ip = other_ip
            work_item = requests.get(f'http://{other_ip}:5000/get_next_work')
            status_code = int (work_item.status_code)
        except:
            return {"status_code":400}
        if status_code != 200:
            return {"status_code":404}
    return work_item.json()

def worker():
    while True:
        work_to_do = get_work_to_do()
        print(work_to_do)
        if work_to_do['status_code'] != 200:
            time.sleep(10)
            continue 
        print(work_to_do.json()['work'])
        work_to_do = work_to_do.json()['work']
        if work_to_do is None:
            time.sleep(10)
            continue
        res = work(work_to_do['data'], work_to_do['iterations'])
        requests.post(f'http://{cur_ip}:5000/completed_work', data={'work_id': work_to_do['work_id'], 'result': res})


def work(buffer, iterations):
    import hashlib
    buffer_bytes = buffer.encode('utf-8')
    output = hashlib.sha512(buffer_bytes).digest()
    for i in range(iterations - 1):
        output = hashlib.sha512(output).digest()
    return output

worker()
