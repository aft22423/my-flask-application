# app.py
import json
import boto3
import botocore
import os
import urllib.request
from flask import Flask,render_template,flash, request, redirect
from werkzeug.utils import secure_filename


s3 = boto3.resource('s3')
csatcalc = boto3.client('lambda')
UPLOAD_FOLDER = '/tmp'

app = Flask(__name__)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SECRET_KEY'] = '***YOUR_ANY_PREFERRED_KEY***'
app.config['BUCKET_NAME'] = '***BUCKET_NAME***'
app.config['LAMBDA_NAME'] = '***LAMBDA_NAME***'

ALLOWED_EXTENSIONS = set(['csv'])

def allowed_file(filename):
	return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def upload2s3(file_name, object_name):
    """
    Function to upload a file to an S3 bucket
    """
    filename = "{}/{}".format(app.config['UPLOAD_FOLDER'],file_name)
    s3_client = boto3.client('s3')
    response = s3_client.upload_file(filename, app.config['BUCKET_NAME'], object_name)

    return response
    

@app.route('/')
@app.route('/upload')
def upload_form():
	return render_template('upload.html')
	
@app.route('/upload', methods=['POST'])
def upload_file():
	if request.method == 'POST':
        # check if the post request has the file part
		if 'file' not in request.files:
			flash('No file part')
			return redirect(request.url)
		file = request.files['file']
		if file.filename == '':
			flash('No file selected for uploading')
			return redirect(request.url)
		if file and allowed_file(file.filename):
			filename = secure_filename(file.filename)
			file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            # check wheter classtype is vILT or ILT to save to different folder <<< In Progress: Plan to change to save in same folder (fix at CSAT-Calc lambda)
			if request.form['classtype']=='vILT':
			    payload = {"key": "data/vILT/{}".format(filename)}
			elif request.form['classtype']=='ILT':
			    payload = {"key": "data/ILT/{}".format(filename)}
			else:
			    flash('Please choose Class Type')
			    return redirect(request.url)
		    # upload .csv file to s3
			upload2s3(filename,payload['key'])
			# invoke CSAT-Calc lambda and wait for response
			csat = csatcalc.invoke(FunctionName=app.config['LAMBDA_NAME'],
                    InvocationType='RequestResponse',      
                    Payload=json.dumps(payload))
                    
			csatscore=json.loads(csat['Payload'].read())
			status = csatscore['statusCode']
			result = csatscore['body']
			# check whether CSAT-Calc is error or not
			if status==400:
			    flash('{}'.format(result))
			    return redirect(request.url)
			tmp=json.loads(result)
			ratio=round((float(tmp['Response'])/float(request.form['attendee']))*100,2)
			return render_template('result.html',result=json.loads(result),attendee=request.form['attendee'], ratio=ratio)
		else:
			flash('Allowed file type is .csv')
			return redirect(request.url)

    
if __name__=='__main__':
    app.run()
