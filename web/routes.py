from flask import Flask, render_template, request

# Flask app config
app = Flask(__name__)
app.debug = True


@app.route('/', methods=['GET'])
@app.route('/index', methods=['GET'])
def route_index():
    tasks = [[0, 'mjbf5f', 'FMX283_Sunny_Side_Up.dvl', '4 hours', 'Running'],
             [6, 'mjbf2f', 'FMV137_Sas_For_Days.dvr', '1 hour', 'Running'],
             [9, 'md3kxa', 'FMX283_Rainy_Snowy.dvl', '3 minutes', 'Waiting']]
    return render_template('index.html', tasks=tasks)


if __name__ == '__main__':
    app.run()