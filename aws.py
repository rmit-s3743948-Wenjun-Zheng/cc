from logging import exception
from os import linesep, path
from types import new_class
from typing import Dict
import boto3
from boto3.dynamodb.conditions import Key, Attr
import json
from botocore.exceptions import ClientError
import requests


aws_access_key_id = "AKIAUXLAEQROAIDMKDGU"
aws_secret_access_key = "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"
region = "us-east-1"
SENDER = "327382065qq@gmail.com"
CONFIGURATION_SET = "ConfigSet"
APIurl = "https://7ubc2ypcqe.execute-api.us-east-1.amazonaws.com/prod"

dynamodb = boto3.resource("dynamodb",aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key, region_name=region)
s3 = boto3.resource("s3",aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key, region_name=region)
SES = boto3.client('ses',aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key, region_name=region)

# check user login 
def checklogin(email, password):
    table = dynamodb.Table("User")
    response = table.query(
        KeyConditionExpression=Key('Account').eq(email),
        FilterExpression=Attr('Password').eq(password)
    )

    if response["Count"] == 0:
        return False
    else:
        return True

# get user by email
def getuser(account):
    table = dynamodb.Table("User")
    response = table.query(
        KeyConditionExpression=Key('Account').eq(account)
    )
    return response["Items"][0]

#check register information
def checkregister(account):
    table = dynamodb.Table("User")
    response = table.query(
        KeyConditionExpression=Key('Account').eq(account),
    )

    if response["Count"] == 0:
        return False
    else:
        return True

#put new user into DB
def putuser(account, user_name, password):
    table = dynamodb.Table("User") 
        
    table.put_item(
        Item = {
            "Account": account,
            "Password": password,
            "User_name": user_name,
            "Email":""
        }
    )

# verify cusotmer email
def verifyemail(email, user):

    table = dynamodb.Table('User')
    table.update_item(

        Key= {
            'Account': user["Account"],
            'User_name': user["User_name"]
        },
        UpdateExpression="set Email=:e",
        ExpressionAttributeValues={
            ':e':email 
        },
    )

    response = SES.verify_email_identity(
        EmailAddress = email
    )

    print(response)
    
# send food list to customer
def sendcode(user, list, fat, calcium):
    
    RECIPIENT = user["Email"]
    SUBJECT = "Health food list"
    BODY_TEXT = ("Health food\r\n")
    BODY_HTML = """
    <html>
<head></head>
    <body>
      <h1>Health food list</h1>
      <table style="text-align:center; width: 100%">
        <tr style="padding-bottom:10px">
          <th>Food</th>
          <th>FoodType</th>
          <th>Fat</th>
          <th>calciumt</th>
        </tr> """ + list + """
      </table>
      <p>
        total fat = """ + str(fat) + """
      </p>
      <p>
        total calcium = """ + str(calcium) + """
      </p>
    </body>
</html>
            """      
    CHARSET = "UTF-8"

    try: 
         #Provide the contents of the email.
        response = SES.send_email(
            Destination={
                'ToAddresses': [
                    RECIPIENT
                ],
            },
            Message={
                'Body': {
                    'Html': {
                        'Charset': CHARSET,
                        'Data': BODY_HTML,
                    },
                    'Text': {
                        'Charset': CHARSET,
                        'Data': BODY_TEXT,
                    },
                },
                'Subject': {
                    'Charset': CHARSET,
                    'Data': SUBJECT,
                 },
            },
            Source="327382065qq@gmail.com"
        )
    
    except ClientError as e:
        print(e.response['Error']['Message'])    
    else:
         print("Email sent! Message ID:"),
         print(response['MessageId'])

# put new food into DB with API and lambda
def putfood():

    url = ' https://7ubc2ypcqe.execute-api.us-east-1.amazonaws.com/prod/DynamoDBManager'
    
    data = { 

       "operation": "create",

       "tableName": "User",
       
       "payload": {
           
           "Item": {
               
               "Account": "123",
               
               "User_name": "Wen",

               "Email": "1323@qq.com",

               "Password": "123456",

               "Role": "normal"
            }
        }
    }

    response = requests.post(url=url, data=json.dumps(data))
    return response.text

# use api to trigger lambda to create a cluster and run mapreduce program on EMR
def EMRcompute(output):


    url = "https://7ubc2ypcqe.execute-api.us-east-1.amazonaws.com/prod/compute"

    data = {
        "output": output
    }

    response = requests.post(url=url, data=json.dumps(data))

# get s3 path 
def getlist(bucket_name, prefix):

    try:
        bucket=bucket_name
        my_bucket = s3.Bucket(bucket)
        prefix_objs = my_bucket.objects.filter(Prefix=prefix)
        Dict = {}
        list = []

        for obj in prefix_objs:
            key = obj.key
            body =obj.get()['Body'].read()

            str1 = body.decode('UTF-8')

            if(str1 != ""):
                lines = str1.split("\n")
                for  line in lines:
                    if (line != ""):
                        foodkey = line.split("\t")[0]
                        value =  int(line.split("\t")[1])
                        Dict[foodkey] = value

        new = sorted(Dict.items(),  key=lambda d: d[1], reverse=True)[:10]

        for item in new:
            list.append(item)

        if(len(list) == 0):
            return 0
        else:
            return list

    except exception:
        return 1

# upate MapReduce input file
def updateinput(user, foodlist):

    str1 = ""
    for item in foodlist:
        str1 = str1 + user + " select " + item["food"] + "\n"

    binary_data = str1.encode(encoding="utf-8")

    object = s3.Object('assignment-emr', 'Input/input.txt')
    origion =object.get()['Body'].read()
    new = origion +  binary_data 

    object.put(Body=new)

# update current email
def updateEmail(email):
    url = ' https://7ubc2ypcqe.execute-api.us-east-1.amazonaws.com/prod/DynamoDBManager'

    data1 = { 

       "operation": "update",

       "tableName": "CurrentEmail",
       
       "payload": {
           "Key": {
               "Account": "current"
           },
           "UpdateExpression": "set Email = :email",
           "ExpressionAttributeValues": {
               ":email": email
            },
        
            "ReturnValues" : "NONE"
        }
    }

    response = requests.post(url=url, data=json.dumps(data1))

def updatePath(path):
    
    table = dynamodb.Table('Output')

    table.update_item(
        Key={
            "Account": "current"
        },
        UpdateExpression="set #t = :path",
        ExpressionAttributeValues={
            ":path":path
        },
        ExpressionAttributeNames={
            "#t": "Path"
        }
    )


def getpath():
    table = dynamodb.Table("Output")
    response = table.query(
        KeyConditionExpression=Key('Account').eq("current")
    )
    return response["Items"][0]

        

