import requests
import json
import urllib3
import re
import os
import time
import pprint

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

#Input-Data
vmanage_ip = '10.1.60.61'
vmanage_port = ':8443'
headers = {'Content-Type': 'application/json'}
body = ''
master_wOSPF_templateId = '8666f3d9-746a-4be3-bd99-6f59e6c4d14c'

#Start session with vManage
request_url = '/j_security_check'
sess = requests.session()
r = sess.post('https://' + vmanage_ip + vmanage_port + request_url, verify=False, auth=('admin','admin'))

#Select the student and validate the input
list = [ '01','02','03','04','05','06','07','08','10','11','12','13','14','15','16','17','18','19','20','21','22','23','24','25','26','27','28','29','30' ]
stud_num = raw_input('Student-Number [(0)X]: ')
if stud_num in list:
    number = int(stud_num.lstrip('0'))
else:
    print 'Please try again and only input 1-30.'
    exit()

#Determine pod specific object names and variables
b2_vedge_name = 's' + stud_num + 'b2-vEdge'
b3_vedge_name = 's' + stud_num + 'b3-vEdge'
b2_stud_template = ('s%sb2_Device_Template' % stud_num)
b3_stud_template = ('s%sb3_Device_Template' % stud_num)
b2_stud_template_V02 = ('s%sb2_Device_Template_V02' % stud_num)
stud_ospf_template = ('s%s_OSPF' % stud_num)
stud_localpolicy = ('s%s_Local_OSPF_Branch_2' % stud_num)

if number <= 10:
    csp_ip = '10.1.60.26'
    csp_po = '106'
elif number >= 21:
    csp_ip = '10.1.60.28'
    csp_po = '108'
elif number >= 11 and number <= 20:
    csp_ip = '10.1.60.27'
    csp_po = '107'
print 'WISP-CSP IP is ' + csp_ip
print 'CSP Port-Channel is ' + csp_po

#Open reference file for uuid to vedge mappings
#Save uuid to variable
with open('./input-files/uuid-mapping-keyed.json') as uuid_mapping:
    uuid_list = json.loads(uuid_mapping.read())
b2_vedge_uuid = uuid_list[b2_vedge_name]['vedge-uuid']
b3_vedge_uuid = uuid_list[b3_vedge_name]['vedge-uuid']
print 'UUID-Mappings Loaded'
print ('s' + stud_num + 'b2-vEdge-UUID is ' + b2_vedge_uuid)
print ('s' + stud_num + 'b3-vEdge-UUID is ' + b3_vedge_uuid)

#Decommission vEdges
request_url = '/dataservice/system/device/decommission/' + b2_vedge_uuid
r = sess.put('https://' + vmanage_ip + vmanage_port + request_url, verify=False, auth=('admin','admin'))
request_url = '/dataservice/system/device/decommission/' + b3_vedge_uuid
r = sess.put('https://' + vmanage_ip + vmanage_port + request_url, verify=False, auth=('admin','admin'))
print 'vEdge(s) has(have) been successfully decommissioned.'

#Delete Bootstrap Files from Linux VM
os.system('rm -rf ./vedge-bootstraps/s%sb2*' % stud_num)
os.system('rm -rf ./vedge-bootstraps/s%sb3*' % stud_num)
os.system('rm -rf ./vedge-bootstraps/DoNotUse_s%sb2*' % stud_num)
os.system('rm -rf ./vedge-bootstraps/DoNotUse_s%sb3*' % stud_num)
print 'Bootstrap Files have been deleted from Linux VM.'

#Delete Bootstrap Files from NFS
os.system('sshpass -p \'C1sco123\' ssh -o StrictHostKeyChecking=no root@10.1.60.251 \'rm -f /var/WISP-NFS/repository/s%sb2*\'' % stud_num)
os.system('sshpass -p \'C1sco123\' ssh -o StrictHostKeyChecking=no root@10.1.60.251 \'rm -f /var/WISP-NFS/repository/s%sb3*\'' % stud_num)
os.system('sshpass -p \'C1sco123\' ssh -o StrictHostKeyChecking=no root@10.1.60.251 \'rm -f /var/WISP-NFS/repository/DoNotUse_s%sb2*\'' % stud_num)
os.system('sshpass -p \'C1sco123\' ssh -o StrictHostKeyChecking=no root@10.1.60.251 \'rm -f /var/WISP-NFS/repository/DoNotUse_s%sb3*\'' % stud_num)
print 'Bootstrap Files have been deleted from NFS.'

#Delete Services from CSP
print ('Script is attempting to shutdown and delete vEdge Services for Student' + stud_num + ' - Please Wait!')
headers = {'Content-Type': 'application/vnd.yang.data+json'}
request_url = '/api/running/services/'
r = requests.get('https://' + csp_ip + request_url, verify=False, auth=('admin','C1sc023#'), json=body, headers=headers)
if r.status_code is 200:
    csp_services = str(r.json())

    if b2_vedge_name in csp_services:
        #Shutdown and Delete b2-vedge
        headers = {'Content-Type': 'application/vnd.yang.data+json'}
        request_url = '/api/running/services/service/' + b2_vedge_name
        r = requests.get('https://' + csp_ip + request_url, verify=False, auth=('admin','C1sc023#'), json=body, headers=headers)
        if r.status_code is 200:
            #Shutdown b2-vedge from WISP-CSP
            body = {'service': {'power': 'off'}}
            headers = {'Content-Type': 'application/vnd.yang.data+json'}
            request_url = '/api/running/services/service/' + b2_vedge_name
            r = requests.patch('https://' + csp_ip + request_url, verify=False, auth=('admin','C1sc023#'), json=body, headers=headers)
            if r.status_code is 204:
                #Delete b2-vedge from WISP-CSP
                print('Service ' + b2_vedge_name + ' has been shutdown.')
                headers = {'Content-Type': 'application/vnd.yang.data+json'}
                request_url = '/api/running/services/service/' + b2_vedge_name
                r = requests.delete('https://' + csp_ip + request_url, verify=False, auth=('admin','C1sc023#'), json=body, headers=headers)
                if r.status_code is 204:
                    print ('Service ' + b2_vedge_name + ' has been deleted.')
    else:
        print (b2_vedge_name + ' is not deployed on ' + csp_ip)

    if b3_vedge_name in csp_services:
        #Shutdown and Delete b3-vedge
        headers = {'Content-Type': 'application/vnd.yang.data+json'}
        request_url = '/api/running/services/service/' + b3_vedge_name
        r = requests.get('https://' + csp_ip + request_url, verify=False, auth=('admin','C1sc023#'), json=body, headers=headers)
        if r.status_code is 200:
            #Shutdown b3-vedge from WISP-CSP
            body = {'service': {'power': 'off'}}
            headers = {'Content-Type': 'application/vnd.yang.data+json'}
            request_url = '/api/running/services/service/' + b3_vedge_name
            r = requests.patch('https://' + csp_ip + request_url, verify=False, auth=('admin','C1sc023#'), json=body, headers=headers)
            if r.status_code is 204:
                #Delete b3-vedge from WISP-CSP
                print('Service ' + b3_vedge_name + ' has been shutdown.')
                headers = {'Content-Type': 'application/vnd.yang.data+json'}
                request_url = '/api/running/services/service/' + b3_vedge_name
                r = requests.delete('https://' + csp_ip + request_url, verify=False, auth=('admin','C1sc023#'), json=body, headers=headers)
                if r.status_code is 204:
                    print ('Service ' + b3_vedge_name + ' has been deleted.')
    else:
        print (b3_vedge_name + ' is not deployed on ' + csp_ip)
else:
    #Exit Script    
   print 'There are no Services running on ' + csp_ip

#Get list of device templates
request_url = '/dataservice/template/device/'
r = sess.get('https://' + vmanage_ip + vmanage_port + request_url, verify=False, auth=('admin','admin'))
template_list_json = r.json()
template_list = template_list_json['data']

#Get list of feature templates
request_url = '/dataservice/template/feature/'
r = sess.get('https://' + vmanage_ip + vmanage_port + request_url, verify=False, auth=('admin','admin'))
feature_list_json = r.json()
feature_list = feature_list_json['data']

#Get list of local policies
request_url = '/dataservice/template/policy/vedge'
r = sess.get('https://' + vmanage_ip + vmanage_port + request_url, verify=False, auth=('admin','admin'))
policy_list_json = r.json()
policy_list = policy_list_json['data']

#Get templateIds from template list
b2_stud_templateId = "False"
b3_stud_templateId = "False"
b2_stud_templateId_V02 = "False"
stud_ospf_templateId = "False"
stud_localpolicyId = "False"

for idx, val in enumerate(template_list):
    if val['templateName'] == b2_stud_template:
        b2_stud_templateId = val['templateId']

for idx, val in enumerate(template_list):
    if val['templateName'] == b3_stud_template:
        b3_stud_templateId = val['templateId']

for idx, val in enumerate(template_list):
    if val['templateName'] == b2_stud_template_V02:
        b2_stud_templateId_V02 = val['templateId']

for idx, val in enumerate(feature_list):
    if val['templateName'] == stud_ospf_template:
        stud_ospf_templateId = val['templateId']

for idx, val in enumerate(policy_list):
    if val['policyName'] == stud_localpolicy:
        stud_localpolicyId = val['policyId']

#Delete Templates
#b2_stud_templateId
if b2_stud_templateId is "False":
    print b2_stud_template + ' does not exist or is misnamed.'
else:
    request_url = '/dataservice/template/device/' + b2_stud_templateId
    r = sess.delete('https://' + vmanage_ip + vmanage_port + request_url, verify=False, auth=('admin','admin'))
    if r.status_code is 200:
        print (b2_stud_template + ' has been deleted.')
    else:
        print r.status_code
        print 'Failed to delete ' + b2_stud_template

#b3_stud_templateId
if b3_stud_templateId is "False":   
    print b3_stud_template + ' does not exist or is misnamed.'
else:
    request_url = '/dataservice/template/device/' + b3_stud_templateId
    r = sess.delete('https://' + vmanage_ip + vmanage_port + request_url, verify=False, auth=('admin','admin'))
    if r.status_code is 200:
        print (b3_stud_template + ' has been deleted.')
    else:
        print 'Failed to delete ' + b3_stud_template

#b2_stud_template_V02
if b2_stud_templateId_V02 is "False":
    print b2_stud_template_V02 + ' does not exist or is misnamed.'
else:
    request_url = '/dataservice/template/device/' + b2_stud_templateId_V02
    r = sess.delete('https://' + vmanage_ip + vmanage_port + request_url, verify=False, auth=('admin','admin'))
    if r.status_code is 200:
        print (b2_stud_template_V02 + ' has been deleted.')
    else:
        print 'Failed to delete ' + b2_stud_template_V02

#stud_ospf_template
if stud_ospf_templateId is "False":
    print stud_ospf_template + ' does not exist or is misnamed.'
else:
    request_url = '/dataservice/template/feature/' + stud_ospf_templateId
    r = sess.delete('https://' + vmanage_ip + vmanage_port + request_url, verify=False, auth=('admin','admin'))
    if r.status_code is 200:
        print (stud_ospf_template + ' has been deleted.')
    else:
        print 'Failed to delete ' + stud_ospf_template

#stud_localpolicy
if stud_localpolicyId is "False":
    print stud_localpolicy + ' does not exist or is misnamed.'
else:
    request_url = '/dataservice/template/policy/vedge/' + stud_localpolicyId
    r = sess.delete('https://' + vmanage_ip + vmanage_port + request_url, verify=False, auth=('admin','admin'))
    if r.status_code is 200:
        print (stud_localpolicy + ' has been deleted.')
    else:
        print 'Failed to delete ' + stud_localpolicy