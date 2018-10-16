
list = range(1,31)

config_string = \
"""
interface GigabitEthernet2.1$num
 encapsulation dot1Q 1$num
 ip address 10.1.1$num.2 255.255.255.0
 ip ospf network point-to-point

router ospf 1$num
 network 10.1.1$num.0 0.0.0.255 area 0
"""

new_string = []

for i in list:
    new_string += [
        config_string.replace("$num", str(i).rjust(2,"0"))
    ]

for i, item in zip(list, new_string):
    with open('./input-files/ospf-config.txt', 'a') as file:
        file.write(item)