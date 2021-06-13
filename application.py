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
                "next": "/user",
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
        role =  param.get("Role", "")
        
        if (account == "") | (password == "") | (username == ""):
            return jsonify({"status": "No input"})

        if checkregister(account):
            return jsonify({"status": "failed"})
        else:
            putuser(account, username, password, role)
            createtable(account)
            return jsonify({
                "status": "ok",
                "next": "/",
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

    select = getselectlist(session['user_id'])

    table = ""
    totalfat = 0
    totalcalcium = 0

    for food in select:
        totalfat = totalfat + int(food["fat"])
        totalcalcium = totalcalcium + int(food["calcium"])
        table=table+"""<tr>
          <td>""" + food["food"] + """</td>
          <td>""" + food["foodtype"] + """</td>
          <td>""" + food["fat"] + """</td>
          <td>""" + food["calcium"] + """</td>
        </tr>"""

    sendcode(getuser(session['user_id']), table, totalfat, totalcalcium)
     
    updateinput(session['user_id'], select)

    return jsonify({
                "status": "ok"
            })

@app.route('/addfood', methods=['POST'])
def addfood():
    
    if(getuser(session['user_id'])["Role"] == "Normal"):
        return jsonify({
                "status": "failed"
            })
    
    if "image" not in request.files:
             return jsonify({"status": "No file"})
    
    imagepath = "Foodimage/" + request.form.get("foodname") + ".jpg"
    foodname = request.form.get("foodname") + ", "
    foodtype =  request.form.get("foodtype")
    fat =  request.form.get("fat")
    calcium =  request.form.get("calcium")
    data = request.files["image"]

    food = {
        "foodname" : foodname,
        "foodtype" : foodtype,
        "fat": fat,
        "calcium": calcium
    }
    putfood(food)
    addtostorage("wenjun",imagepath, data)

    return jsonify({
        "status": "ok"
    })

@app.route('/compute', methods=['POST'])
def compute():

    if(getuser(session['user_id'])["Role"] == "Normal"):
        return jsonify({
                "status": "failed"
            })

    if(getuser(session['user_id'])["Email"] == ""):
        return jsonify({
                "status": "error"
            })

    now = datetime.datetime.now()
    output = now.strftime("%Y-%m-%d%H:%M:%S") + "/"

    updateEmail(getuser(session['user_id'])["Email"])
    updatePath(output)
    EMRcompute(output)

    return jsonify({
             "status": "ok"
           })

@app.route('/getfood', methods=['GET'])
def getfood():
    foodlist = getfoodlist()
    list = []


    for item in foodlist:
       
        path = item["food"] + ".jpg"
        template =  """<li id="messagelist">
                                <div class="d-flex align-items-center">
                                    <div class="card mb-3" style="max-width: 600px;">
                                        <div class="row no-gutters align-items-center">
                                          <div class="col-md-3">
                                            <img src= "https://wenjun.s3.amazonaws.com/Foodimage/""" + path + """" class="card-img" alt="Upload image">
                                          </div>
                                          <div class="col-md-8">
                                            <div class="card-body">
                                              <p class="card-text">Food Name:""" + item["food"] + """</p>
                                              <p class="card-text">Food Type: """ + item["foodtype"] + """</p>
                                              <p class="card-text">Total Fat: """ + item["fat"] + """</p>
                                              <p class="card-text">Total Calcium: """ + item["calcium"] + """</p>
                                            </div>
                                          </div>
                                        </div>
                                    </div>
                                    <button type="button" style="margin-left: 5%; margin-right: 3%;" class="btn btn-primary" data-toggle="modal" data-target="#myModal" id="select">
                                        Select
                                    </button>
                                </div>
                            </li>"""
        list.append(template)

    return jsonify({"status": "ok", "list": list})

@app.route('/select', methods=['POST']) 
def select():
    param = json.loads(request.data.decode("utf-8"))
    name = param.get("foodname", "")
    type = param.get("foodtype", "")
    fat = param.get("totalfat", "")
    calcium = param.get("totalcalcium", "")
    food = {"name": name, "type": type, "fat": fat, "calcium": calcium}
    selectfood(food, session['user_id'])
    
    return jsonify({"status": "ok"})

@app.route('/getlist', methods=['GET']) 
def getlist():
    select = getselectlist(session['user_id'])
    list = []

    for item in select:
       
        path = item["food"] + ".jpg"
        template =  """<li id="messagelist">
                                <div class="d-flex align-items-center">
                                    <div class="card mb-3" style="max-width: 600px;">
                                        <div class="row no-gutters align-items-center">
                                          <div class="col-md-3">
                                            <img src= "https://wenjun.s3.amazonaws.com/Foodimage/""" + path + """" class="card-img" alt="Upload image">
                                          </div>
                                          <div class="col-md-8">
                                            <div class="card-body">
                                              <p class="card-text">Food Name:""" + item["food"] + """</p>
                                              <p class="card-text">Food Type: """ + item["foodtype"] + """</p>
                                              <p class="card-text">Total Fat: """ + item["fat"] + """</p>
                                              <p class="card-text">Total Calcium: """ + item["calcium"] + """</p>
                                            </div>
                                          </div>
                                        </div>
                                    </div>
                                    <button type="button" style="margin-left: 5%; margin-right: 3%;" class="btn btn-primary" data-toggle="modal" data-target="#myModal" id="remove">
                                        Remove
                                    </button>
                                </div>
                            </li>"""
        list.append(template)

    return jsonify({"status": "ok", "list": list})

@app.route('/getpopular', methods=['GET','POST'])
def getpopular():
    path = "output/" + getpath()["Path"]
    popularlist = getpopularlist("assignment-emr1", path)
    
    print(popularlist)

    if (popularlist == 0):
        return jsonify({
                "status": "error",
            })

    return jsonify({
        "status": "ok",
        "list":  popularlist
    })

@app.route('/remove', methods=['POST']) 
def remove():
    param = json.loads(request.data.decode("utf-8"))
    param = json.loads(request.data.decode("utf-8"))
    name = param.get("foodname", "")
    type = param.get("foodtype", "")
    fat = param.get("totalfat", "")
    calcium = param.get("totalcalcium", "")
    food = {"name": name, "type": type, "fat": fat, "calcium": calcium}
    removefood(food, session['user_id'])
    return jsonify({"status": "ok"})

@app.route('/foodlist', methods=['GET', 'POST'])
def foodlist():
    if request.method == "GET":
        if not g.user:
            return redirect(url_for("login"))
        return render_template('Foodlist.html')

    elif request.method == "POST":
        session.pop('user_id', None)
        return jsonify({"next": "/"})

@app.route('/user',methods=['GET', 'POST'])
def root():
    if request.method == "GET":
        if not g.user:
            return redirect(url_for("login"))
        current = getuser(session['user_id'])
        message = ""

        if (current["Email"] == ""):
            message = "You do not regist any email, please click register email button"
        else:
            message = "Your Regist Email: " + current["Email"]
        
        return render_template("User.html", message=message)
    elif request.method == "POST":
        session.pop('user_id', None)
        return jsonify({"next": "/"})

@app.route('/email', methods=['GET', 'POST'])
def email():
    if request.method == "GET":
        if not g.user:
            return redirect(url_for("login"))
        return render_template('Email.html')
    elif request.method == "POST":
        session.pop('user_id', None)
        return jsonify({"next": "/"})

@app.route('/add', methods=['GET', 'POST'])
def add():
    if request.method == "GET":
        if not g.user:
            return redirect(url_for("login"))
        return render_template('Add.html')
    elif request.method == "POST":
        session.pop('user_id', None)
        return jsonify({"next": "/"})


@app.route('/popular')
def popular():
    if request.method == "GET":
        if not g.user:
            return redirect(url_for("login"))
        return render_template('Popular.html')
    elif request.method == "POST":
        session.pop('user_id', None)
        return jsonify({"next": "/"})


# example test
@app.route('/123')
def example():
    list = getfood()
    return render_template("login.html", results=list)
      
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
   
