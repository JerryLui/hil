""" Adds required folders, run this for setup. """

import os

file_folder = os.path.dirname(os.path.abspath(__file__))
to_create = [os.path.join(file_folder, 'hil', 'tmp', 'uploads'),
             os.path.join(file_folder, 'hil', 'static', 'db')]

for folder in to_create:
    try:
        os.mkdir(folder)
    except OSError:
        print('Folder already exists!')
