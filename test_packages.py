import os
import subprocess

reqs = open("requirements.txt", 'r')
s = reqs.read()
with open("requirements.txt") as reqs:
    content = reqs.readlines()
content = [x.strip() for x in content]
# print(content)
content = [x.split("==")[0] for x in content]
# print(content)
os.system("cd")
print("activate")
os.system(r"venv\Scripts\activate")
print("pip")
os.system("where pip")


for p in content:
    # info = os.system("pip show " + p)
    output: str = str(subprocess.check_output("pip show " + p))
    print(p + ": " + output)
    info = output.split("Location: ")[1]
    location = info.split("Requires:")[0][:-4]
    # print("info:", info)
    # print(p + ":")
    print(p + ":", location)

# input("waiting for key")
# # uninstalling
# for p in content:
#     print(p)
#
# os.system("pip list")
