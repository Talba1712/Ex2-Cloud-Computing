from flask import Flask, request, session
import json
import uuid
import boto3
import json
import time
import boto3
import threading
import requests
import sys

first_endpoint_ip = sys.argv[1]
second_endpoint_ip = sys.argv[2]
access_key_id = sys.argv[3]
secret_access_key = sys.argv[4]

session = boto3.Session(
    region_name='us-east-1',
    aws_access_key_id=access_key_id,
    aws_secret_access_key=secret_access_key
)

ec2Resource = session.resource('ec2')
ec2Client = session.client('ec2')

app = Flask(__name__)

work_q = []
completed_work_q = []
workers = []

@app.route('/enqueue', methods=['PUT'])
def enqueue():
    iterations = int(request.args.get('iterations'))
    data = request.get_data(as_text=True)
    work_id = str(uuid.uuid1())
    work_entry_time = time.time()
    work_q.append({'work_id': work_id, 'work_entry_time': work_entry_time, 'iterations': iterations, 'data': data})
    return {
        'statusCode': 200,
        'body': json.dumps({'work_id': work_id})
    }

@app.route('/pullCompleted', methods=['POST'])
def pullCompleted():
    top = int(request.args.get('top'))
    other_endpoint_completed_work_q = []
    res = []

    if len(completed_work_q) < top:
        try:
            req = requests.get(f'http://{second_endpoint_ip}:{5000}/getCompletedWorkQ')
            if req.status_code == 200:
                other_endpoint_completed_work_q = req.json()['completed_work_q']
        except:
            other_endpoint_completed_work_q = []
    
    all_completed_work = other_endpoint_completed_work_q + completed_work_q

    k = min(top, len(all_completed_work))
    for i in range(k):
        work = all_completed_work.pop()
        res.append(json.load(work)) 

    return {
        'statusCode': 200,
        'body': json.dumps({'latest_completed_work_items': res})
    }

@app.route('/get_next_work')
def get_next_work():
    if len(work_q) > 0:
        return {'work': work_q.pop(0)}, 200 
    return '' , 404 

@app.route('/completed_work')
def completed_work():
    completed_work_q.append((request.form.get('work_id'), request.form.get('result')))
    return '', 200

@app.route('/getCompletedWorkQ')
def getCompletedWorkQ():
    return {
        'statusCode': 200,
        'body': json.dumps({'completed_work_q': completed_work_q})
    }

def createNewWorker():
    security_group = ec2Client.describe_security_groups(Filters=[dict(Name="group-name", Values=['my-sg'])])
    security_group_id = security_group['SecurityGroups'][0]['GroupId']
    instance = ec2Resource.create_instances(
        MinCount=1,
        MaxCount=1,
        ImageId="ami-042e8287309f5df03",
        InstanceType="t2.micro",
        KeyName="cloud-course-`date +'%N'`",
        UserData=f"""#!/bin/bash
                set -e -x
                sudo apt update
                sudo apt install git -y
                sudo pwd
                sudo git clone https://github.com/Talba1712/Ex2-Cloud-Computing.git
                sudo cp Ex2-Cloud-Computing/worker.py /home/ubuntu/worker.py
                sudo apt install python3 -y
                sudo apt install python3-pip -y
                sudo pip install boto3
                # run app
                nohup python3 Ex2-Cloud-Computing/worker.py $first_endpoint_ip $second_endpoint_ip &>/dev/null &
                exit
                """
        )
    instance[0].wait_until_running()
    instance[0].reload()
    data = ec2Client.authorize_security_group_ingress(
        GroupId=security_group_id,
        IpPermissions=[
            {'IpProtocol': 'tcp',
            'FromPort': 5000,
            'ToPort': 5000,
            'IpRanges': [{'CidrIp': f'{instance[0].public_ip_address}/32'}]},
        ])
    workers.append(instance[0].id)
    return instance[0].id

def timeInQueue(work):
    return time.time() - work['work_entry_time']

def scaling():
    while True:
        create_new_worker = False
        for work in work_q:
            if timeInQueue(work) > 3 and len(work_q) > 5:
                new_worker_id = createNewWorker()
                workers.append(new_worker_id)
                create_new_worker = True
        if not create_new_worker and len(workers) > 0:
            ec2Resource.instances.filter(InstanceIds = workers[0]).terminate()

thread = threading.Thread(target=scaling)
thread.start()
app.run('0.0.0.0', port=5000)
