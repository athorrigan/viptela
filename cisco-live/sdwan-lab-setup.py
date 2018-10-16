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

#Select the session and validate the input
list = ['1','2','12']
lab_sess = raw_input('Lab Session [1 or 2 or 12 (Both)]: ')
if lab_sess in list:
    print ('student%s is completing Lab Session ' % stud_num) + lab_sess 
else:
    print 'Please try again and only input 1, 2 or 12 (Both).'
    exit()

#Determine pod specific object names and variables
b2_vedge_name = 's' + stud_num + 'b2-vEdge'
b3_vedge_name = 's' + stud_num + 'b3-vEdge'
b2_stud_template = ('s%sb2_Device_Template' % stud_num)
b3_stud_template = ('s%sb3_Device_Template' % stud_num)

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

#Using uuid, request bootstraps for b2-vedge and b3-vedge
#Save tokens to variables

#b2_vedge_token
request_url = '/dataservice/system/device/bootstrap/device/' + b2_vedge_uuid + '?configtype=cloudinit'
r = requests.get('https://' + vmanage_ip + vmanage_port + request_url, verify=False, auth=('admin','admin'))
b2_vedge_bootstrap = str(r.json())
b2_vedge_token = re.search(r'otp\s?:\s?(\w+)', b2_vedge_bootstrap)
if b2_vedge_token:
    print  b2_vedge_name + ' OTP-Token is ' + (b2_vedge_token.group(1))

#b3_vedge_token
request_url = '/dataservice/system/device/bootstrap/device/' + b3_vedge_uuid + '?configtype=cloudinit'
r = sess.get('https://' + vmanage_ip + vmanage_port + request_url, verify=False, auth=('admin','admin'))
b3_vedge_bootstrap = str(r.json())
b3_vedge_token = re.search(r'otp\s?:\s?(\w+)', b3_vedge_bootstrap)
if b3_vedge_token:
    print  b3_vedge_name + ' OTP-Token is ' + (b3_vedge_token.group(1))

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

#Deploy Services on WISP-CSP

if lab_sess == '1':
    b2_deploy = False if raw_input('Deploy ' + b2_vedge_name + ' [Y or N]: ').lower() == 'n' else True

    #Copy and move the vedge-user_data into the user_data file in /Viptela
    #Create b2-vedge-bootstrap.iso
    #Copy b2-vedge-bootstrap.iso to WISP-NFS

    os.system('cp ./vedge-bootstraps/s%sb2-vedge-user_data.txt Viptela/openstack/latest/user_data' % stud_num)
    os.system('mkisofs -J -R -V config-2 -o ./vedge-bootstraps/s%sb2-vedge-bootstrap.iso Viptela/' % stud_num)
    os.system('sshpass -p \'C1sco123\' scp -o StrictHostKeyChecking=no ./vedge-bootstraps/s%sb2-vedge-bootstrap.iso root@10.1.60.251:/var/WISP-NFS/repository' % stud_num)
    print ('s%sb2-vedge-bootstrap.iso created and copied to WISP-NFS' % stud_num)

    if b2_deploy == True:
        print ('Deploying vEdge Service on ' + csp_ip + ' - Please Wait!')
        #Deploy b2-vedge on WISP-CSP
        headers = {'Content-Type': 'application/vnd.yang.data+json'}
        request_url = '/api/running/services/'
        body = json.loads(open('./input-files/b2-vedge-csp-template.txt').read().replace("$stud_num", stud_num).replace("$csp_po", csp_po))
        r = requests.post('https://' + csp_ip + request_url, verify=False, auth=('admin','C1sc023#'), json=body, headers=headers)
        print 'Response Code: ' + str(r.status_code)
        print b2_vedge_name + ' deployed on ' + csp_ip

        #Exit script
        print 'Operation Successful'
        exit()

elif lab_sess == '2':

    #Copy and move the vedge-user_data into the user_data file in /Viptela
    #Create b2-vedge-bootstrap.iso
    #Copy b2-vedge-bootstrap.iso to WISP-NFS

    #b2-vedge-user_data
    os.system('cp ./vedge-bootstraps/s%sb2-vedge-user_data.txt Viptela/openstack/latest/user_data' % stud_num)
    os.system('mkisofs -J -R -V config-2 -o ./vedge-bootstraps/s%sb2-vedge-bootstrap.iso Viptela/' % stud_num)
    os.system('sshpass -p \'C1sco123\' scp -o StrictHostKeyChecking=no ./vedge-bootstraps/s%sb2-vedge-bootstrap.iso root@10.1.60.251:/var/WISP-NFS/repository' % stud_num)
    print ('s%sb2-vedge-bootstrap.iso created and copied to WISP-NFS' % stud_num)

    #b3-vedge-user_data
    os.system('cp ./vedge-bootstraps/s%sb3-vedge-user_data.txt Viptela/openstack/latest/user_data' % stud_num)
    os.system('mkisofs -J -R -V config-2 -o ./vedge-bootstraps/s%sb3-vedge-bootstrap.iso Viptela/' % stud_num)
    os.system('sshpass -p \'C1sco123\' scp -o StrictHostKeyChecking=no ./vedge-bootstraps/s%sb3-vedge-bootstrap.iso root@10.1.60.251:/var/WISP-NFS/repository' % stud_num)
    print ('s%sb3-vedge-bootstrap.iso created and copied to WISP-NFS' % stud_num)

    print ('Deploying vEdge Services on ' + csp_ip + ' - Please Wait!')
    #Deploy b2-vedge on WISP-CSP
    headers = {'Content-Type': 'application/vnd.yang.data+json'}
    request_url = '/api/running/services/'
    body = json.loads(open('./input-files/b2-vedge-csp-template.txt').read().replace("$stud_num", stud_num).replace("$csp_po", csp_po))
    r = requests.post('https://' + csp_ip + request_url, verify=False, auth=('admin','C1sc023#'), json=body, headers=headers)
    print 'Response Code: ' + str(r.status_code)
    print b2_vedge_name + ' deployed on ' + csp_ip

    #Deploy b3-vedge on WISP-CSP
    headers = {'Content-Type': 'application/vnd.yang.data+json'}
    request_url = '/api/running/services/'
    body = json.loads(open('./input-files/b3-vedge-csp-template.txt').read().replace("$stud_num", stud_num).replace("$csp_po", csp_po))
    r = requests.post('https://' + csp_ip + request_url, verify=False, auth=('admin','C1sc023#'), json=body, headers=headers)
    print 'Response Code: ' + str(r.status_code)
    print b2_vedge_name + ' deployed on ' + csp_ip

    #Get Master_Branch_Template and copy to create b2_stud_template
    #Post Student_Branch_Template
    request_url = '/dataservice/template/device/object/' + master_wOSPF_templateId
    r = sess.get('https://' + vmanage_ip + vmanage_port + request_url, verify=False, auth=('admin','admin'))
    b2_master_template_body = r.json()
    b2_master_template_body['templateName'] = b2_stud_template 
    b2_master_template_body['templateDescription'] = b2_stud_template
    print 'Master_Branch_Template copied to create ' + b2_stud_template 

    request_url = '/dataservice/template/device/feature/'
    r = sess.post('https://' + vmanage_ip + vmanage_port + request_url, verify=False, auth=('admin','admin'), json=b2_master_template_body)
    if r.status_code is 200:
        print b2_stud_template + ' has been created.'
    else:
        print 'Template copying has failed.  Please ensure the template does not already exist on vManage.'
    
    #Get Master_Branch_Template and copy to create b3_stud_template
    #Post Student_Branch_Template
    request_url = '/dataservice/template/device/object/' + master_wOSPF_templateId
    r = sess.get('https://' + vmanage_ip + vmanage_port + request_url, verify=False, auth=('admin','admin'))
    b3_master_template_body = r.json()
    b3_master_template_body['templateName'] = b3_stud_template 
    b3_master_template_body['templateDescription'] = b3_stud_template
    print 'Master_Branch_Template copied to create ' + b3_stud_template 

    request_url = '/dataservice/template/device/feature/'
    r = sess.post('https://' + vmanage_ip + vmanage_port + request_url, verify=False, auth=('admin','admin'), json=b3_master_template_body)
    if r.status_code is 200:
        print b3_stud_template + ' has been created.'
    else:
        print 'Template copying has failed.  Please ensure the template does not already exist on vManage.'

    #Get list of templates
    request_url = '/dataservice/template/device/'
    r = sess.get('https://' + vmanage_ip + vmanage_port + request_url, verify=False, auth=('admin','admin'))
    template_list_json = r.json()
    template_list = template_list_json['data']
    print 'List of templates retreived.'

    #Get templateIds for b2 and b3_stud_template from template list
    for idx, val in enumerate(template_list):
        if val['templateName'] == b2_stud_template:
            b2_stud_templateId = val['templateId']
        if val['templateName'] == b3_stud_template:
            b3_stud_templateId = val['templateId']

    #Attach b2 and b3_stud_templates
    headers = {'Content-Type': 'application/json', 'cache-control': 'no-cache', 'accept': '*/*', 'accept-encoding': 'gzip, deflate'}
    request_url = '/dataservice/template/device/config/attachfeature/'
    body = json.loads(open('./input-files/b2-vedge-attachfeature-template.txt').read().replace("$stud_num", stud_num).replace("$vedge_uuid", b2_vedge_uuid).replace("$stud_templateId" , b2_stud_templateId))
    pprint.pprint(body)
    r = sess.post('https://' + vmanage_ip + vmanage_port + request_url, verify=False, auth=('admin','admin',), json=body, headers=headers)
    if r.status_code is 200:
        print (b2_stud_template + ' has been attached to ' + b2_vedge_name)
    else:
        print r.status_code
        print 'Template failed to attach to ' + b2_vedge_name

    body = json.loads(open('./input-files/b3-vedge-attachfeature-template.txt').read().replace("$stud_num", stud_num).replace("$vedge_uuid", b3_vedge_uuid).replace("$stud_templateId" , b3_stud_templateId))
    pprint.pprint(body)
    r = sess.post('https://' + vmanage_ip + vmanage_port + request_url, verify=False, auth=('admin','admin',), json=body, headers=headers)
    if r.status_code is 200:
        print (b3_stud_template + ' has been attached to ' + b3_vedge_name)
    else:
        print r.status_code
        print 'Template failed to attach to ' + b3_vedge_name

    #Exit script
    print 'Operation Sucessful. Please wait (~120sec) for process to complete!'
    exit()

elif lab_sess == '12':

    #Copy and move the vedge-user_data into the user_data file in /Viptela
    #Create b2-vedge-bootstrap.iso
    #Copy b2-vedge-bootstrap.iso to WISP-NFS

    #b2-vedge-user_data
    os.system('cp ./vedge-bootstraps/s%sb2-vedge-user_data.txt Viptela/openstack/latest/user_data' % stud_num)
    os.system('mkisofs -J -R -V config-2 -o ./vedge-bootstraps/s%sb2-vedge-bootstrap.iso Viptela/' % stud_num)
    os.system('sshpass -p \'C1sco123\' scp -o StrictHostKeyChecking=no ./vedge-bootstraps/s%sb2-vedge-bootstrap.iso root@10.1.60.251:/var/WISP-NFS/repository' % stud_num)
    print ('s%sb2-vedge-bootstrap.iso created and copied to WISP-NFS' % stud_num)

    #b3-vedge-user_data
    os.system('cp ./vedge-bootstraps/s%sb3-vedge-user_data.txt Viptela/openstack/latest/user_data' % stud_num)
    os.system('mkisofs -J -R -V config-2 -o ./vedge-bootstraps/DoNotUse_s%sb3-vedge-bootstrap.iso Viptela/' % stud_num)
    os.system('sshpass -p \'C1sco123\' scp -o StrictHostKeyChecking=no ./vedge-bootstraps/DoNotUse_s%sb3-vedge-bootstrap.iso root@10.1.60.251:/var/WISP-NFS/repository' % stud_num)
    print ('DO-NOT-USE_s%sb3-vedge-bootstrap.iso created and copied to WISP-NFS' % stud_num)

    print ('Deploying vEdge Services on ' + csp_ip + ' - Please Wait!')
    #Deploy b3-vedge on WISP-CSP
    headers = {'Content-Type': 'application/vnd.yang.data+json'}
    request_url = '/api/running/services/'
    body = json.loads(open('./input-files/b3-vedge-csp-template-12.txt').read().replace("$stud_num", stud_num).replace("$csp_po", csp_po))
    r = requests.post('https://' + csp_ip + request_url, verify=False, auth=('admin','C1sc023#'), json=body, headers=headers)
    print 'Response Code: ' + str(r.status_code)
    print b2_vedge_name + ' deployed on ' + csp_ip
    
    #Get Master_Branch_Template and copy to create b3_stud_template
    #Post Student_Branch_Template
    request_url = '/dataservice/template/device/object/' + master_wOSPF_templateId
    r = sess.get('https://' + vmanage_ip + vmanage_port + request_url, verify=False, auth=('admin','admin'))
    b3_master_template_body = r.json()
    b3_master_template_body['templateName'] = b3_stud_template 
    b3_master_template_body['templateDescription'] = b3_stud_template
    print 'Master_Branch_Template copied to create ' + b3_stud_template 

    request_url = '/dataservice/template/device/feature/'
    r = sess.post('https://' + vmanage_ip + vmanage_port + request_url, verify=False, auth=('admin','admin'), json=b3_master_template_body)
    if r.status_code is 200:
        print b3_stud_template + ' has been created.'
    else:
        print 'Template copying has failed.  Please ensure the template does not already exist on vManage.'

    #Get list of templates
    request_url = '/dataservice/template/device/'
    r = sess.get('https://' + vmanage_ip + vmanage_port + request_url, verify=False, auth=('admin','admin'))
    template_list_json = r.json()
    template_list = template_list_json['data']
    print 'List of templates retreived.'

    #Get templateIds for b2 and b3_stud_template from template list
    for idx, val in enumerate(template_list):
        if val['templateName'] == b3_stud_template:
            b3_stud_templateId = val['templateId']

    #Attach b3_stud_templates
    headers = {'Content-Type': 'application/json', 'cache-control': 'no-cache', 'accept': '*/*', 'accept-encoding': 'gzip, deflate'}
    request_url = '/dataservice/template/device/config/attachfeature/'
    body = json.loads(open('./input-files/b3-vedge-attachfeature-template.txt').read().replace("$stud_num", stud_num).replace("$vedge_uuid", b3_vedge_uuid).replace("$stud_templateId" , b3_stud_templateId))
    pprint.pprint(body)
    r = sess.post('https://' + vmanage_ip + vmanage_port + request_url, verify=False, auth=('admin','admin',), json=body, headers=headers)
    if r.status_code is 200:
        print (b3_stud_template + ' has been attached to ' + b3_vedge_name)
    else:
        print r.status_code
        print 'Template failed to attach to ' + b3_vedge_name

    #Exit script
    print 'Operation Sucessful. Please wait (~120sec) for process to complete!'
    exit()

