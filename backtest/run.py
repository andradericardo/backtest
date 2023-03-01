import json

def run_simulation(backtest):
    backtest.set_calendar()
    backtest.load_sectors_data()
    backtest.load_mkt_portfolio()
    backtest.run()
    backtest.save_results()
    
    
def run(amago, data_obj, series, config="config.json", test=False):
    print("Loading:", config)
    with open(config, "r") as file:
        config_data = json.load(file)

    default = config_data["default"]
    simulations = config_data["simulations"]

    objs = list()
    for simulation in simulations:
        print("Starting simulation:", simulation["name"])
        params = default.copy()
        params.update(simulation)

        obj = amago(**params)
        obj.add_data(data_obj)
        obj.add_series(series)

        run_simulation(obj)
        objs.append(obj)
        print("Done!", obj.name)
    
    return objs[0] if test else objs
