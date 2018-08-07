# LOOPER

### Installation:
Ensure the required packages are installed by running 

```pip3 install -r requirements.txt```

Then configure application with device specific settings at start of `routes.py` in `app.config['DEVICE_HOST']` and `app.config['DEVICE_LOG_DRIVE']`.
Finally run the application by running

```python3 routes.py```

### Improvements:
- Add aspera connect to host to be able to directly download a log and run (there's a cli verison available).
- If order of execution is important implement Queue in multiprocessing.