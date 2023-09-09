import os


extensions = [".py", ".ini"]
extensions_bl = [".pyc"]

with open("VersionNumber") as f:
    version = f.readline()
version = version.replace("\n", "")

file_list = []
for path, subdirs, files in os.walk(os.getcwd()):
    for name in files:
        file_path = os.path.join(path, name)
        if any(x in file_path for x in extensions):
            if not any(x in file_path for x in extensions_bl):
                file_list.append(file_path)


for filename in file_list:
    if "version_update.py" not in filename:
        update = False
        with open(filename, 'r') as f:
            lines = f.readlines()
            for line in lines:
                if "version = " in line:
                    line = "version = " + version
                    update = True
            if update is True:
                with open(filename, 'w') as f:
                    print("Version number updated in: " + filename)
                    for line in lines:
                        if "version = " in line:
                            line = "version = " + version + "\n"
                        f.write(line)
