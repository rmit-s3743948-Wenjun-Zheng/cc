from os import path
from botocore.hooks import _PrefixTrie
from flask import Flask, render_template, request, redirect, jsonify, g, session, url_for
from aws import *
import json
import datetime

application = app = Flask(__name__)
app.config['SECRET_KEY']="asdfghjkl"

@app.before_request
def before_request():
    g.user = None
    if 'user_id' in session:
        g.user = getuser(session['user_id'])
        
@app.route('/', methods=['GET', 'POST']) 
def root(): 
    if request.method == "GET":
        if not g.user:
            return redirect(url_for("login"))
        return render_template('Main.html')
    elif request.method == "POST":
        session.pop('user_id', None)
        return jsonify({"next": "/login"})

@app.route('/login', methods=['GET', 'POST']) 
def login(): 
   if request.method == "GET":
       return render_template("Login.html")
   elif request.method == "POST":
        session.pop('user_id', None)
        param = json.loads(request.data.decode("utf-8"))
        account = param.get("Account", "")
        password = param.get("password", "")

        if checklogin(account, password):
            session['user_id'] = account
            return jsonify({
                "status": "ok",
                "next": "/",
            })
        else:
            return jsonify({"status": "failed"})


@app.route('/register', methods=['GET', 'POST']) 
def Register(): 
    if request.method == "GET":
        return render_template('Register.html')
    elif request.method == "POST":
        param = json.loads(request.data.decode("utf-8"))
        account = param.get("Account", "")
        password = param.get("password", "")
        username = param.get("username", "")

        if checkregister(account):
            return jsonify({"status": "failed"})
        else:
            putuser(account, username, password)
            return jsonify({
                "status": "ok",
                "next": "/login",
            })

@app.route('/addemail', methods=['POST'])
def addemail():
    param = json.loads(request.data.decode("utf-8"))
    email = param.get("email", "")

    verifyemail(email,g.user)

    return jsonify({
                "status": "ok"
            })

@app.route('/sendlist', methods=['POST'])
def sendlist():

    if(getuser(session['user_id'])["Email"] == ""):
        return jsonify({
                "status": "failed"
            })

    param = json.loads(request.data.decode("utf-8"))
    foodlist = param.get("list", "")

    table = ""
    totalfat = 0
    totalcalcium = 0

    for food in foodlist:
        totalfat = totalfat + food["fat"]
        totalcalcium = totalcalcium + food["calcium"]
        table=table+"""<tr>
          <td>""" + str(food["food"]) + """</td>
          <td>""" + str(food["foodtype"]) + """</td>
          <td>""" + str(food["fat"]) + """</td>
          <td>""" + str(food["calcium"]) + """</td>
        </tr>"""

    sendcode(getuser(session['user_id']), table, totalfat, totalcalcium)
     
    updateinput(session['user_id'], foodlist)

    return jsonify({
                "status": "ok"
            })

@app.route('/addfood', methods=['POST'])
def addfood():
    
    if(getuser(session['user_id'])["Role"] == "normal"):
        return jsonify({
                "status": "failed"
            })
    
    #get food information from request
    param = json.loads(request.data.decode("utf-8"))

    response = putfood()

    if (response == "1"):
        return jsonify({
            "status": "ok"
        })
    else:
        return jsonify({
             "status": "error",
             "message": response
           })

@app.route('/compute', methods=['POST'])
def compute():

    if(getuser(session['user_id'])["Role"] == "normal"):
        return jsonify({
                "status": "failed"
            })

    now = datetime.datetime.now()
    output = now.strftime("%Y-%m-%d%H:%M:%S") + "/"

    updateEmail(getuser(session['user_id'])["Email"])
    updatePath(output)
    EMRcompute(output)

    return jsonify({
             "status": "ok"
           })

@app.route('/show', methods=['POST'])
def show():

    if(getuser(session['user_id'])["Role"] == "normal"):
        return jsonify({
                "status": "failed"
            })

    path = "output/" + getpath()["Path"]
    print(path)
    list = getlist("assignment-emr", path)
    if (list == 0):
         return jsonify({
                "status": "error",
            })
    
    else:
        return jsonify({
                "status": "ok",
                "data": list
            })
    
    

# example test
@app.route('/123')
def example():

    return render_template("123.html", results=[{"food": "apple","foodtype": "fruit","fat": 10,"calcium": 10},{"food": "tuna","foodtype": "seafood","fat": 20,"calcium": 30}])


      
if __name__ == '__main__':
    # This is used when running locally only. When deploying to Google App
    # Engine, a webserver process such as Gunicorn will serve the app. This
    # can be configured by adding an `entrypoint` to app.yaml.

    # Flask's development server will automatically serve static files in
    # the "static" directory. See:
    # http://flask.pocoo.org/docs/1.0/quickstart/#static-files. Once deployed,
    # App Engine itself will serve those files as configured in app.yaml.
    app = application
    app.debug = True
    app.run()
   
