import requests
import json
import urllib3
import re
import os
import time
import pprint

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

#Connection Information
vmanage_ip = '10.1.60.61:8443'
request_url = '/j_security_check'
sess = requests.session()
r = sess.post('https://' + vmanage_ip + request_url, verify=False, auth=('admin','admin'))


#Select the student and validate the input
list = [ '01','02','03','04','05','06','07','08','10','11','12','13','14','15','16']
stud_num = raw_input('Student-Number [(0)X]: ')
if stud_num in list:
    number = int(stud_num.lstrip('0'))
else:
    print 'Please try again and only input 1-16.'
    exit()


#Determine input values using student number
b2_vedge_name = ('s%sb2-vEdge' % stud_num)
b3_vedge_name = ('s%sb3-vEdge' % stud_num)
b2_stud_template = ('s%sb2_Device_Template' % stud_num)
b3_stud_template = ('s%sb3_Device_Template' % stud_num)
if number <= 8:
    csp_ip = '10.1.60.26'
    csp_po = '106'
else:
    csp_ip = '10.1.60.27'
    csp_po = '107'
with open('./input-files/uuid-mapping-keyed.json') as uuid_mapping:
    uuid_list = json.loads(uuid_mapping.read())
b2_vedge_uuid = uuid_list[b2_vedge_name]['vedge-uuid']
b3_vedge_uuid = uuid_list[b3_vedge_name]['vedge-uuid']
print (b2_vedge_name + (' (%s) will deploy on ' % b2_vedge_uuid) + csp_ip)
print (b3_vedge_name + (' (%s) will deploy on ' % b3_vedge_uuid) + csp_ip)


#Using UUID, request bootstraps for b2-vedge and b3-vedge
#Save tokens to variables
#b2_vedge_token
request_url = '/dataservice/system/device/bootstrap/device/' + b2_vedge_uuid + '?configtype=cloudinit'
r = requests.get('https://' + vmanage_ip + request_url, verify=False, auth=('admin','admin'))
b2_vedge_bootstrap = str(r.json())
b2_vedge_token = re.search(r'otp\s?:\s?(\w+)', b2_vedge_bootstrap)
#b3_vedge_token
request_url = '/dataservice/system/device/bootstrap/device/' + b3_vedge_uuid + '?configtype=cloudinit'
r = sess.get('https://' + vmanage_ip + request_url, verify=False, auth=('admin','admin'))
b3_vedge_bootstrap = str(r.json())
b3_vedge_token = re.search(r'otp\s?:\s?(\w+)', b3_vedge_bootstrap)


#Replace variables in the user_data template
#Create vedge-user_data file
#b2-vedge-user_data
with open('./input-files/b2-vedge-bootstrap-template.txt', 'rb') as in_file:
    text = in_file.readlines()
with open('./vedge-bootstraps/s%sb2-vedge-user_data.txt' % stud_num, 'w') as out_file:
    for  line in text:
        out_file.write(line.replace('$vedge_token' , str(b2_vedge_token.group(1))).replace('$vedge_uuid' , str(b2_vedge_uuid)).replace('$stud_num' , str(stud_num)))
print b2_vedge_name + '-user_data files created'
#b3-vedge-user_data
with open('./input-files/b3-vedge-bootstrap-template.txt', 'rb') as in_file:
    text = in_file.readlines()
with open('./vedge-bootstraps/s%sb3-vedge-user_data.txt' % stud_num, 'w') as out_file:
    for  line in text:
        out_file.write(line.replace('$vedge_token' , str(b3_vedge_token.group(1))).replace('$vedge_uuid' , str(b3_vedge_uuid)).replace('$stud_num' , str(stud_num)))
print b3_vedge_name + '-user_data files created'


#Copy and move the vedge-user_data into the user_data file in /Viptela
#Create vedge-bootstrap.iso for B2 and B3
#Copy both vedge-bootstrap.iso files to WISP-NFS
#b2-vedge-user_data
print ('Creating bootstrap file for ' + b2_vedge_name)
os.system('cp ./vedge-bootstraps/s%sb2-vedge-user_data.txt Viptela/openstack/latest/user_data' % stud_num)
os.system('mkisofs -J -R -V config-2 -o ./vedge-bootstraps/s%sb2-vedge-bootstrap.iso Viptela/' % stud_num)
os.system('sshpass -p \'C1sco123\' scp -o StrictHostKeyChecking=no ./vedge-bootstraps/s%sb2-vedge-bootstrap.iso root@10.1.60.251:/var/WISP-NFS/repository' % stud_num)
#b3-vedge-user_data
print ('Creating bootstrap file for ' + b3_vedge_name)
os.system('cp ./vedge-bootstraps/s%sb3-vedge-user_data.txt Viptela/openstack/latest/user_data' % stud_num)
os.system('mkisofs -J -R -V config-2 -o ./vedge-bootstraps/s%sb3-vedge-bootstrap.iso Viptela/' % stud_num)
os.system('sshpass -p \'C1sco123\' scp -o StrictHostKeyChecking=no ./vedge-bootstraps/s%sb3-vedge-bootstrap.iso root@10.1.60.251:/var/WISP-NFS/repository' % stud_num)


#Deploy vedges on WISP-CSP
#b2-vedge
headers = {'Content-Type': 'application/vnd.yang.data+json'}
request_url = '/api/running/services/'
body = json.loads(open('./input-files/b2-vedge-csp-template.txt').read().replace("$stud_num", stud_num).replace("$csp_po", csp_po))
r = requests.post('https://' + csp_ip + request_url, verify=False, auth=('admin','C1sc023#'), json=body, headers=headers)
if r.status_code is 200:
    print (b2_vedge_name + ' is successfully deploying on ' + csp_ip)
#b3-vedge
headers = {'Content-Type': 'application/vnd.yang.data+json'}
request_url = '/api/running/services/'
body = json.loads(open('./input-files/b3-vedge-csp-template.txt').read().replace("$stud_num", stud_num).replace("$csp_po", csp_po))
r = requests.post('https://' + csp_ip + request_url, verify=False, auth=('admin','C1sc023#'), json=body, headers=headers)    
if r.status_code is 200:
    print (b3_vedge_name + ' is successfully deploying on ' + csp_ip)