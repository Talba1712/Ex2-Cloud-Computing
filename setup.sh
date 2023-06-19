#!/bin/bash

ACCESS_KEY_ID=$(aws configure get aws_access_key_id)
SECRET_ACCESS_KEY=$(aws configure get aws_secret_access_key)
KEY_NAME="cloud-course-`date +'%N'`"
KEY_PEM="$KEY_NAME.pem"

echo "create key pair $KEY_PEM to connect to instances and save locally"
aws ec2 create-key-pair --key-name $KEY_NAME | jq -r ".KeyMaterial" > $KEY_PEM

# secure the key pair
chmod 400 $KEY_PEM

SEC_GRP="my-sg-`date +'%N'`"

echo "setup firewall $SEC_GRP"
aws ec2 create-security-group   \
    --group-name $SEC_GRP       \
    --description "Access my instances" 

# figure out my ip
MY_IP=$(curl ipinfo.io/ip)
echo "My IP: $MY_IP"


echo "setup rule allowing SSH access to only ips"
aws ec2 authorize-security-group-ingress        \
    --group-name $SEC_GRP --port 22 --protocol tcp \
    --cidr 0.0.0.0/0

echo "setup rule allowing HTTP (port 5000) access to all ips"
aws ec2 authorize-security-group-ingress        \
    --group-name $SEC_GRP --port 5000 --protocol tcp \
    --cidr 0.0.0.0/0

UBUNTU_20_04_AMI="ami-042e8287309f5df03"

#FirstInstance
echo "Creating Ubuntu 20.04 instance..."
RUN_INSTANCES1=$(aws ec2 run-instances  \
    --image-id $UBUNTU_20_04_AMI        \
    --instance-type t3.micro            \
    --key-name $KEY_NAME                \
    --security-groups $SEC_GRP)

INSTANCE_ID1=$(echo $RUN_INSTANCES1 | jq -r '.Instances[0].InstanceId')

echo "Waiting for the first instance creation..."
aws ec2 wait instance-running --instance-ids $INSTANCE_ID1

PUBLIC_IP1=$(aws ec2 describe-instances --instance-ids $INSTANCE_ID1 | 
    jq -r '.Reservations[0].Instances[0].PublicIpAddress'
)

echo "New instance $INSTANCE_ID1 @ $PUBLIC_IP1"

#SecondInstance
echo "Creating Ubuntu 20.04 instance..."
RUN_INSTANCES2=$(aws ec2 run-instances  \
    --image-id $UBUNTU_20_04_AMI        \
    --instance-type t3.micro            \
    --key-name $KEY_NAME                \
    --security-groups $SEC_GRP)

INSTANCE_ID2=$(echo $RUN_INSTANCES2 | jq -r '.Instances[0].InstanceId')

echo "Waiting for the second instance creation..."
aws ec2 wait instance-running --instance-ids $INSTANCE_ID2

PUBLIC_IP2=$(aws ec2 describe-instances --instance-ids $INSTANCE_ID2 | 
    jq -r '.Reservations[0].Instances[0].PublicIpAddress'
)

echo "New instance $INSTANCE_ID2 @ $PUBLIC_IP2"


echo "deploying code to production"
scp -i $KEY_PEM -o "StrictHostKeyChecking=no" -o "ConnectionAttempts=60" app.py ubuntu@$PUBLIC_IP1:/home/ubuntu/
scp -i $KEY_PEM -o "StrictHostKeyChecking=no" -o "ConnectionAttempts=60" app.py ubuntu@$PUBLIC_IP2:/home/ubuntu/

echo "setup production environment for the first instance"
ssh -i $KEY_PEM -o "StrictHostKeyChecking=no" -o "ConnectionAttempts=60" ubuntu@$PUBLIC_IP1 <<EOF
    sudo apt update
    sudo apt install python3 -y
    sudo apt install python3-flask -y
    sudo apt install python3-pip -y
    pip install boto3
    # run app
    nohup python3 app.py $PUBLIC_IP1 $PUBLIC_IP2 $ACCESS_KEY_ID $SECRET_ACCESS_KEY &>/dev/null &
    exit
EOF

echo "setup production environment for the second instance"
ssh -i $KEY_PEM -o "StrictHostKeyChecking=no" -o "ConnectionAttempts=60" ubuntu@$PUBLIC_IP2 <<EOF
    sudo apt update
    sudo apt install python3 -y
    sudo apt install python3-flask -y
    sudo apt install python3-pip -y
    pip install boto3
    # run app
    nohup python3 app.py $PUBLIC_IP2 $PUBLIC_IP1 $ACCESS_KEY_ID $SECRET_ACCESS_KEY &>/dev/null &
    exit
EOF

sleep 90
echo "test that it all worked"

curl   http://$PUBLIC_IP1:5000
curl   http://$PUBLIC_IP2:5000
