import requests
import json
import urllib3
import re
import os
import time
import pprint
import httplib

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
httplib.HTTPConnection.debuglevel = 5

#Select the student and lab session
#Inputs must match specified patterns
stud_num = raw_input('Student-Number [(0)X]: ')
number = int(stud_num.lstrip('0'))
b2_vedge_name = 's' + stud_num + 'b2-vEdge'
b3_vedge_name = 's' + stud_num + 'b3-vEdge'

#Open reference file for uuid to vedge mappings
#Save uuid to variable
with open('./input-files/uuid-mapping-keyed.json') as uuid_mapping:
    uuid_list = json.loads(uuid_mapping.read())
b2_vedge_uuid = uuid_list[b2_vedge_name]['vedge-uuid']
b3_vedge_uuid = uuid_list[b3_vedge_name]['vedge-uuid']

#Input-Data
vmanage_ip = '10.1.60.61'
vmanage_port = ':8443'
headers = {'Content-Type': 'application/json'}
body = ''
master_templateId = '8666f3d9-746a-4be3-bd99-6f59e6c4d14c'
stud_template = ('s%sb2_Device_Template' % stud_num)

#Start session with vManage
request_url = '/j_security_check'
sess = requests.session()
r = sess.post('https://' + vmanage_ip + vmanage_port + request_url, verify=False, auth=('admin','admin'))

#Get Master_Branch_Template
request_url = '/dataservice/template/device/object/' + master_templateId
r = sess.get('https://' + vmanage_ip + vmanage_port + request_url, verify=False, auth=('admin','admin'))
master_template_body = r.json()
master_template_body['templateName'] = stud_template 
master_template_body['templateDescription'] = stud_template
print 'Master_Branch_Template copied to create ' + stud_template 

#Post Master_Branch_Template
request_url = '/dataservice/template/device/feature/'
r = sess.post('https://' + vmanage_ip + vmanage_port + request_url, verify=False, auth=('admin','admin'), json=master_template_body)
if r.status_code is 200:
    print stud_template + ' has been created.'
else:
    print 'Template copying has failed.  Please ensure the template does not already exist on vManage.'

#Get list of templates
request_url = '/dataservice/template/device/'
r = sess.get('https://' + vmanage_ip + vmanage_port + request_url, verify=False, auth=('admin','admin'))
template_list_json = r.json()
template_list = template_list_json['data']

#Get templateId from template list
for idx, val in enumerate(template_list):
    if val['templateName'] == stud_template:
        stud_templateId = val['templateId']

#Post Master_Branch_Template
headers = {'Content-Type': 'application/json', 'cache-control': 'no-cache', 'accept': '*/*', 'accept-encoding': 'gzip, deflate'}
request_url = '/dataservice/template/device/config/attachfeature/'
body = json.loads(open('./input-files/b2-vedge-attachfeature-template.txt').read().replace("$stud_num", stud_num).replace("$vedge_uuid", b2_vedge_uuid).replace("$stud_templateId" , stud_templateId))
r = sess.post('https://' + vmanage_ip + vmanage_port + request_url, verify=False, auth=('admin','admin',), json=body, headers=headers)
if r.status_code is 200:
    print (stud_template + ' has been attached to ' + b2_vedge_name)
else:
    print r.status_code
    print 'Template failed to attach to ' + b2_vedge_name
