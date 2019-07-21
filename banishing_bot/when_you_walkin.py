import os

# for dirname, dirnames, filenames in os.walk('.'):
#     # print path to all subdirectories first.
#     for subdirname in dirnames:
#         print(os.path.join(dirname, subdirname))

#     # print path to all filenames.
#     for filename in filenames:
#         print(os.path.join(dirname, filename))

#     # Advanced usage:
#     # editing the 'dirnames' list will stop os.walk() from recursing into there.
#     if '.git' in dirnames:
#         # don't go into any .git directories.
#         dirnames.remove('.git')

path = os.path.dirname(os.path.abspath(__file__))
print(os.listdir(path))
print(os.listdir(path+'/corpora/words_master_list.txt'))