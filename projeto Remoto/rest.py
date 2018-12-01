from flask import Flask
from flask_restful import Api, Resource, reqparse
import boto3, sys

app = Flask(__name__)
api = Api(app)



bucketname = sys.argv[1]
access_key = sys.argv[2]
secret_key = sys.argv[3]


s3 = boto3.client('s3', region_name="us-east-1", aws_access_key_id = access_key, aws_secret_access_key = secret_key)
s3Resource = boto3.resource('s3', region_name="us-east-1", aws_access_key_id = access_key, aws_secret_access_key = secret_key)


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
    logins = {}
    for name in (s3.list_objects(Bucket=bucketname)['Contents']):
        key = (name['Key'])
        obj = s3Resource.Object(bucketname, name['Key'])
        text = obj.get()['Body'].read().decode('utf-8')
        logins[key] = text
        
    print(logins)
    return logins
    
# Bucket Manager End

#--- Application logic

def get_user_name(name):
    logins = describe_bucket()
    if(name in logins.keys()):
        return(name,logins[name])
    return None


###Endpoints###
class SignUp(Resource):
        
    def post(self,login,password):
        print("post sign up")
        pair = get_user_name(login)
        if(pair != None):
            return ("name taken",400)
        create_text_bucket(login,password)
        return("done",200)
        
        
class SignIn(Resource):

    def get(self,login, password):
        print("get sign in")
        pair = get_user_name(login)
        if(pair == None):
            return ("login not found",400)
        
        if(password == pair[1]):
            return{"You are in" : login, "Secret message for you.." : "Raul me passa!!! Ta mo bonito meu programa"}
        
        return("wrong password",400)

class List(Resource):
    def get(self):
        print("get list")
        return describe_bucket()

class Healthcheck(Resource):
    def get(self):
        return ("",200)
        
        
api.add_resource(SignUp,'/signup/<login>/<password>')
api.add_resource(SignIn,'/signin/<login>/<password>')
api.add_resource(List, '/list', endpoint = 'list')
api.add_resource(Healthcheck,'/healthcheck', endpoint = 'healthcheck')


if __name__ == '__main__':
    app.run(debug = False, host="0.0.0.0", port=5000)


