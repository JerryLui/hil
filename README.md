# HIL
Frontend implementation for Hardware-in-Loop device.

### Installation:
Ensure the required packages are installed by running 

```pip3 install -r requirements.txt```

Then configure application with device specific settings at start of `routes.py` in `app.config['DEVICE_HOST']` and `app.config['DEVICE_LOG_DRIVE']`.
Finally run the application by running

```python3 routes.py```


### Storage structure:
```
log_folder
├── original_logs
│   ├── suite1
│   │   ├── log1_1.dvl
│   │   │   ...
│   │   └── log1_99.dvl
│   ├── suite2
│   │   └── log2_1.dvl
│   │   │   ...
│   │   └── log2_99.dvl
│   └── suite3
│       └── subsuite_1
│       │   └── log3_1_1.dvl
│       │   │   ...
│       │   └── log3_1_99.dvl
│       └── subsuite_2
│           └── log3_2_1.dvl
└── output_logs
```


### Improvements:
- Add aspera connect to host to be able to directly download a log and run (there's a cli verison available).
- If order of execution is important implement Queue in multiprocessing.
