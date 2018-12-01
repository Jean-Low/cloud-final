from flask import Flask, redirect
from flask_restful import Api, Resource, reqparse
import boto3
import time
import sys
import random
import requests as r
from threading import Timer
from botocore.exceptions import ClientError

#--- paths

app = Flask(__name__)
api = Api(app)

access_key = sys.argv[2]
secret_key = sys.argv[3]


ec2Resource = boto3.resource('ec2',region_name = "us-east-1", aws_access_key_id = access_key, aws_secret_access_key = secret_key)

ec2 = boto3.client('ec2', region_name = "us-east-1", aws_access_key_id = access_key, aws_secret_access_key = secret_key)

waiter = ec2.get_waiter('instance_terminated')

#--- Vars

desired_amount = int(sys.argv[1]);

#--- Init

userdataMockUp ='''#!/bin/bash
cd home/ubuntu
mkdir running
git clone https://github.com/Lightclawjl/cloud-projeto
cd cloud-projeto
bash install.sh
python3 rest.py

'''


#--- Managers

def create_instances(amount):
    print("--- Creating {} Instance(s)".format(amount))
    warning = None
    userdata = userdataMockUp
    response = ec2Resource.create_instances(

                        ImageId = 'ami-0ac019f4fcb7cb7e6',
                        MinCount=amount,
                        MaxCount=amount,
                        KeyName="despair",
                        SecurityGroups=[
                            'APS_Jean',
                        ],
                        InstanceType="t2.micro",
                        UserData=userdataMockUp,
                        TagSpecifications=[
                                    {
                                        'ResourceType' : 'instance',
                                        'Tags': [
                                            {
                                                'Key': 'owner',
                                                'Value': 'jean'
                                            },
                                            {
                                                'Key': 'loader',
                                                'Value': 'False'
                                            },
                                        ]
                                    },
                                ]
                    )
    return(True, response, warning)

###Endpoints###
@app.route('/', defaults={"path":''})
@app.route('/<path:path>')
def catch_all(path):
    global desired_amount
    if(path == "healthcheck"):
        return ('ok',200)
    
    if(path == "checkamount"):
        return ('The desired amount is currently {}'.format(desired_amount))
    
    splited = path.split('/')
    print(splited)
    if(splited[0] == "setamount"):
        amount = None
        try:
            amount = int(splited[1])
        except:
            amount = None
        if(amount == None):
            return ('ERROR: Invalid amount')
        desired_amount = amount
        return ("updated desired amount",200)
    
    choice = random.choice(list(active_instances.keys()))
    
    if(choice == None):
        return ('error',400)
    newpath = "http://" + choice + ":5000/" + path
    return redirect(newpath, code=302)


def update():
    global setup_instances
    print("\n---Status checking---")
    iplist = active_instances.keys()
    ips_to_remove = []
    for ip in iplist:
        print("Checking {}".format(ip))
        test = "http://{}:5000/healthcheck".format(ip)
        #print(test)
        passed = False
        try: 
            r.get(test,timeout = 3.0)
            passed = True
        except:
            passed = False
        if(passed):
            print("Ok")
        else:
            print("Malfunction")
            print("--Removing {}".format(ip))
            ec2.terminate_instances(InstanceIds=[active_instances[ip]])
            ips_to_remove.append(ip)
            
    for ip in ips_to_remove:
        active_instances.pop(ip,None)
    
    if len(active_instances.keys()) != desired_amount :
        print("There are {} machines".format(len(active_instances)))
        print("Correcting machines to desired amount ({})".format(desired_amount))
        dif = desired_amount - len(active_instances.keys())
        if(dif < 0):
            print("The are more machines than desired, reducing")
            iplist = active_instances.keys()
            ips_to_remove = []
            for ip in iplist:
                print("--Removing {}".format(ip))
                instanceIds = []
                instanceIds.append(active_instances[ip])
                print(instanceIds)
                try:
                    ec2.terminate_instances(InstanceIds= instanceIds)
                except:
                    print("Could not terminate instance {}".format(ip))
                    print("Manual check required")
                    print("Removed from loadbalacer anyways")
                ips_to_remove.append(ip)
                dif += 1
                if dif == 0:
                    break
                    
            for ip in ips_to_remove:
                active_instances.pop(ip,None)
                print("Removed {}".format(ip))
                
        elif (dif > 0):
            if(len(setup_instances) > 0):
                amount = len(setup_instances)
                print("There are {} machines are in set up stage".format(amount))
                for i in range(amount):
                    setup_instances[i][0].load()
                    
                    ip = setup_instances[i][0].public_ip_address
                    up = setup_instances[i][1]
                    if(up):
                        test = "http://{}:5000/healthcheck".format(ip)
                        passed = False
                        try: 
                            r.get(test,timeout = 8.0)
                            passed = True
                        except:
                            pass
                        
                        if(passed):
                            print("A new machine is running. ({})".format(setup_instances[i][0].id))
                            active_instances[ip] = setup_instances[i][0].id
                            setup_instances.pop(i)
                        else:
                            print("Machine {} is still waiting for server...".format(setup_instances[i][0].id))
                            
                    elif (ip != None):
                        setup_instances[i][1] = True
                        print("Machine {} is up, waiting for server".format(setup_instances[i][0].id))
                        

                
            else:
                print("There are less machines than desired, increasing")
                response = create_instances(dif)[1]
                setup_instances = []
                for i in response:
                    setup_instances.append([i,False])
                print("Launching {} new instances".format(len(setup_instances)))
                
            #while (dif != 0):
                #print("--Adding")
                #response = create_instance()
                #print(response[1])
                #print(ip + " -- " + response[1][0].id)
                #active_instances[ip] = response[1][0].public_ip_address
                #print(active_instances.keys())
                #dif -= 1
        print("Now there are {} machines".format(len(active_instances.keys())))
    print("Done!")
    Timer(20.0, update).start()

#Run routine

print("Running load balancer")

active_instances = {}
setup_instances = [] #format (instace, times until timeout)


for i in ec2Resource.instances.filter(Filters=[{ 
        'Name' : 'instance-state-name', 
        'Values' : ['running']
        },
        { 
        'Name' : 'tag:owner', 
        'Values' : ['jean']
        },
        {
        'Name' : 'tag:loader', 
        'Values' : ['False']
        }]):
            print("makina")
            print(i.id)
            active_instances[i.public_ip_address] = i.id

print(active_instances.keys())
        

#start check
Timer(5.0,update).start()

if __name__ == '__main__':
    app.run(debug = False, host="0.0.0.0", port=5000)













