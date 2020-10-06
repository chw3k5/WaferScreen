import codecs
file = "C:\\Program Files (x86)\\STARCryo\\ADRControlPanel\\SupportFiles\\Lin_10TurnsCW.bin"

with open(file=file, mode="rb") as f:
    lines = f.readlines()
encoding = 'ascii-85'
row = lines[0]
for i in range(1, len(row)):
    print(encoding, row[0: i].decode(encoding=encoding, errors='ignore'))

