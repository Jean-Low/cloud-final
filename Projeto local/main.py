import boto3
import time
import sys
from botocore.exceptions import ClientError

#--- paths

ec2 = boto3.client('ec2')

ec2Resource = boto3.resource('ec2')

s3 = boto3.client('s3')

s3Resource = boto3.resource('s3')

waiter = ec2.get_waiter('instance_terminated')

credentials = boto3.Session().get_credentials()

#---

# BIBLE
# 1 - Time is relative to your despair level
# 2 - Response objects have the format (<Bool success>,<AWS response object>,<String warning (optional)>)
# 3 - when deleting, use a "sure" variable to assure that you deleted something that existed
# 4 - It is better to delivery a good product but late, than a mal-functioning one in schedule



#--- Key management

#--- User friendly coding
defMockUp = '''
def func_name():
    print("--- What I do")
    warning = None
    response = "AWS stuff"
    return(True, response, warning)
'''


def describe_key_pairs():
    return ec2.describe_key_pairs()

def create_key_pair(keyname, save = True):
    print("--- Creating a keypair named " + keyname)
    warning = None
    keys = describe_key_pairs()['KeyPairs']
    for pairs in keys:
        if keyname == pairs['KeyName']:
            delete_key_pair(keyname, sure = True)
            warning = "Replaced an Existing KeyPair (" + keyname + ")"
            break
    response = ec2.create_key_pair(KeyName = keyname)
    
    if(save):
        outfile = open("key/" + keyname + ".pem", "w")
        outfile.write(str(response["KeyMaterial"]))
        outfile.close()
    return (True, response, warning)

def delete_key_pair(keyname, sure = False):
    print('--- Deleting KeyPair named ' + keyname)
    warning = None
    if(not sure):
        keys = describe_key_pairs()['KeyPairs']
        for pairs in keys:
            if keyname == pairs['KeyName']:
                sure = True
                break
    if(not sure):
        warning = "No key named " + keyname + " found."
        return (True, None, warning)
        
    response = ec2.delete_key_pair(KeyName=keyname)
    return (True, response, warning)
    

# Key management end



#--- Security Groups Management
def describe_security_group(groupname):
    warning = None
    try:
        response = ec2.describe_security_groups(GroupNames=[groupname])['SecurityGroups'][0]
        return (True, response, warning)
    except ClientError as e:
        warning = "Client Error"
        return (False, e, warning)
        
def create_security_group(groupname):
    print("--- Creating Security Group named " + groupname)
    warning = None
    
    #Check if exist and delete if it does
    attempt = describe_security_group(groupname)
    if(attempt[0] == True): #meaning a group already exist
        warning = "Replaced an existing Security Group (" + groupname + ")"
        delete_security_group(groupname, sure = True)
    
    response = ec2.describe_vpcs()
    vpc_id = response.get('Vpcs', [{}])[0].get('VpcId', '')
    
    try:
        response = ec2.create_security_group(GroupName=groupname,
                                             Description='Testing',
                                             VpcId=vpc_id)
        security_group_id = response['GroupId']
        print('Security Group Created %s in vpc %s.' % (security_group_id, vpc_id))

        data = ec2.authorize_security_group_ingress(
            GroupId=security_group_id,
            IpPermissions=[
                    {'IpProtocol': 'tcp',
                        'FromPort': 80,
                        'ToPort': 80,
                        'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
                    {'IpProtocol': 'tcp',
                        'FromPort': 22,
                        'ToPort': 22,
                        'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
                    {'IpProtocol': 'tcp',
                        'FromPort': 5000,
                        'ToPort': 5000,
                        'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
                    ]
            )        
        #print('Ingress Successfully Set %s' % data) running
        return(True, response, warning)
    except ClientError as e:
        return(True, e, "Client Error")
    
def delete_security_group(groupname, sure = False):
    print("--- Deleting security group with name " + groupname)
    warning = None
    if(not sure):
        attempt = describe_security_group(groupname)
        if(attempt[0] == False):
            warning = "No security group named " + groupname
            return (False, None, warning)
    try:
        response = ec2.delete_security_group(GroupName=groupname)
        return(True, response, warning)
    except ClientError as e:
        return(False, e, "Client Error")

# Security Groups Management End



#--- Instance Managemente
def describe_instances():
    return ec2.describe_instances()

def create_instances(amount ,loadbalancer = False):
    print("--- Creating {} Instance".format(amount))
    warning = None
    userdata = userdataMockUp
    if(loadbalancer):
        userdata = loadbalancerInit
    response = ec2Resource.create_instances(

                        ImageId = 'ami-0ac019f4fcb7cb7e6',
                        MinCount=amount,
                        MaxCount=amount,
                        KeyName="despair",
                        SecurityGroups=[
                            'APS_Jean',
                        ],
                        InstanceType="t2.micro",
                        UserData=userdata,
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
                                                'Value': str(loadbalancer)
                                            },
                                        ]
                                    },
                                ]
                    )
    return(True, response, warning)

def delete_my_instances():
    print("--- Terminating all my intances")
    current_instances = ec2Resource.instances.filter(Filters=[{
        'Name' : 'instance-state-name',
        'Values' : ['running']}]
    )
    
    instanceIds = []
    
    for i in current_instances:
        for tag in i.tags:
            if tag['Value'] == "jean":
                print("Intance " + i.id + " will be terminated")
                instanceIds.append(i.id)
                break
    if(len(instanceIds) == 0):
        print("No intance to shutdown")
        return
    ec2.terminate_instances(InstanceIds=instanceIds)
    
    print("Waiting for shutdown")
    waiter.wait(InstanceIds=instanceIds)
    print("Done")
        
# Instance Management End

#--- Bucket Manager

def create_bucket(name):
    print("--- Creating a bucket named " + name)
    warning = None
    response = s3.create_bucket(Bucket=name)
    
    return(True, response, warning)

def create_text_bucket(name,text):
    path = "file/" + name
    outfile = open(path, "w")
    outfile.write(str(text))
    outfile.close()
    
    s3.upload_file(path, bucketname,name)

def describe_bucket():
    print("--- Describing bucket files")
    for name in (s3.list_objects(Bucket=bucketname)['Contents']):
        print(name['Key'])
        obj = s3Resource.Object(bucketname, name['Key'])
        text = obj.get()['Body'].read().decode('utf-8')
        print(text)
        


# Bucket Manager End


#--- Vars

initialAmount = int(sys.argv[1])
bucketname = "jeanclouddespair"

if(len(sys.argv) > 2):
    bucketname = str(sys.argv[2])

#print(credentials.access_key)
#print(credentials.secret_key)

userdataMockUp ='''#!/bin/bash
cd home/ubuntu
mkdir running
git clone https://github.com/Lightclawjl/cloud-projeto
cd cloud-projeto
bash install.sh
python3 rest.py {} {} {}

'''.format(bucketname, credentials.access_key, credentials.secret_key)

loadbalancerInit ='''#!/bin/bash
cd home/ubuntu
mkdir Loader
git clone https://github.com/Lightclawjl/cloud-projeto
cd cloud-projeto
bash install.sh
python3 loadbalancer.py {} {} {}

'''.format(initialAmount, credentials.access_key, credentials.secret_key)

#--- Starter

print("--- Running ---")
delete_my_instances()
create_key_pair('despair')
create_security_group("APS_Jean")
create_bucket(bucketname)
create_instances(initialAmount)
print("---Loadbalancer id: {}".format(create_instances(1,loadbalancer = True)))
















