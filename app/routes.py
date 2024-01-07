from flask import render_template, request, jsonify, redirect, url_for,session
from app import app
import requests
from azure.storage.blob import BlobServiceClient
import os
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
app.secret_key = 'random_string'
# Replace with your API Gateway URL
API_GATEWAY_REQUEST_BLOOD = 'https://finalapigateway.azure-api.net/request'
API_GATEWAY_LOGİN = 'https://finalapigateway.azure-api.net/login'
API_GATEWAY_ADD_BLOOD = 'https://finalapigateway.azure-api.net/add'
API_GATEWAY_CREATE_DONOR = 'https://finalapigateway.azure-api.net/create'

load_dotenv()

@app.route('/',methods = ['GET'])
def home():
    return render_template('index.html')

@app.route("/login", methods = ['GET','POST'])
def login():
    # If request method is POST, it comes froms the form, check database and validate user
    if request.method == 'POST':
        user_data = request.form.to_dict()
        
        response = requests.post(API_GATEWAY_LOGİN,json = user_data)
        api_response = response.json()

        status = api_response.get('status')

        if status == 'TRUE':
            api_response = response.json()
            session['logged_in'] = True
            session['username'] = api_response.get('user_name')
            return redirect(url_for('userOpt'))
        else:
            error = 'Wrong username or password'
            return render_template("login.html",error = error)
    # else it is a GET request and we will render login page
    else:
        return render_template("login.html")

@app.route("/userLogged")
def userOpt():
    return render_template("loggedFrame.html")


@app.route('/request', methods=['POST','GET'])
def requestBlood():
    if request.method == 'POST':
        # Retrieve form data from the request
        form_data = request.form.to_dict()
        form_data['units'] = int(form_data.get('units', 0))
        form_data['duration'] = int(form_data.get('duration', 0))
        print(form_data)
        # Make a post request to API GATEWAY
        response = requests.post(API_GATEWAY_REQUEST_BLOOD, json=form_data)
        
        api_response = response.json()

        status = api_response.get('status')
        
        # Check if the request was successful (status code 2xx)
        if status == 'TRUE':
            donor_list = api_response.get('donor_list')
            return render_template("requestblood.html",donors = donor_list)
        else:
            return jsonify({'success': False, 'error': 'API request failed'})
        
    # No security issues no need to communicate with API GATEWAY
    else:
        return render_template('requestblood.html')

@app.route("/add",methods= ['GET','POST'])
def addBlood():
    if 'logged_in' in session and session['logged_in']:
        branch_name = session['username']
        
        if request.method == 'POST':
            form_data = request.form.to_dict()
            
            response = requests.post(API_GATEWAY_ADD_BLOOD, json=form_data)
            api_response = response.json()
            status = api_response.get('status')
            if status=='TRUE':
                message = api_response.get('Message')
                return render_template("addblood.html",branch_name = branch_name,message = message)
        else:
            # We need list of donor names therefore we will send a get request via API GATEWAY
            form_data = {"branch_name":branch_name}
            response = requests.get(API_GATEWAY_ADD_BLOOD,params=form_data)
            try:
                api_response = response.json()
                donor_list = api_response.get('donor_list')
                return render_template("addblood.html",branch_name = branch_name,donor_list = donor_list)
            except:
                print("Non-JSON response received.")
    else:
        return redirect(url_for('login'))


def uploadToBlobStorage(file_storage):
    try:
        blob_service_client = BlobServiceClient.from_connection_string(os.getenv('AZURE_STORAGE_CONNECTION_STRING'))
        container_client = blob_service_client.get_container_client(os.getenv('AZURE_CONTAINER'))

        # Extract the file stream and filename from FileStorage
        stream = file_storage.stream
        filename = secure_filename(file_storage.filename)

        # Upload the file stream to the CDN
        blob_client = container_client.upload_blob(name=filename, data=stream)

        # Obtain the CDN URL from the blob client
        cdn_url = blob_client.url

        return cdn_url

    except Exception as e:
        print(f"Error uploading to CDN: {str(e)}")
        return None
    
@app.route("/create",methods=['GET','POST'])
def createDonor():
    if 'logged_in' in session and session['logged_in']: 
        branch_name = session['username']
        if request.method == 'POST':
            form_data = request.form.to_dict()
            if 'photo' in request.files:
                photo_file = request.files['photo']
                cdn_url = uploadToBlobStorage(photo_file)
                form_data['cdn_url'] = cdn_url
                print(form_data)
                response = requests.post(API_GATEWAY_CREATE_DONOR, json=form_data)
                api_response = response.json()
                status = api_response.get('status')

            if status == 'TRUE':
                message = api_response.get('message')
                return render_template("createdonor.html",branch_name=branch_name,message = message)
        else:
            return render_template("createdonor.html",branch_name = branch_name)
    else:
        return redirect(url_for('login'))
        
@app.route("/logout",methods =['GET'])
def logout():
    session.clear()
    return redirect(url_for('home'))