import io
import matplotlib

matplotlib.use("AGG")
import matplotlib.pyplot as plt
from fastapi import FastAPI, Response, BackgroundTasks

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import pandas as pd
import numpy as np
import uuid

"""
Script which simulates the charging behaviour of a population of EV drivers.

The script reads in a csv file containing the following columns:
- Name: The name of the driver group
- Plug-in time: The time of day the driver plugs in
- Plug-out time: The time of day the driver plugs out
- Plug-in SoC: The state of charge the driver plugs in with
- Target SoC: The state of charge the driver aims to reach
- SoC requirement: The state of charge required to complete the journey
- Miles/yr: The number of miles driven per year
- Efficiency (mi/kWh): The efficiency of the vehicle in miles per kWh
- Battery (kWh): The size of the battery in kWh
- Charger kW: The power of the charger in kW
- Plug-in frequency (per day): The frequency with which the driver plugs in per day
- % of population: The percentage of the population that the driver group represents

The script simulates the charging behaviour of a population of EV drivers by:
- Drawing a random sample from a normal distribution with a standard deviation of 60 minutes to simulate the time at which each driver plugs in
"""


app = FastAPI()

# Set up Jinja2 templates
templates = Jinja2Templates(directory="templates")

# Mount the static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")


# Home page route
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


"""
# Simulator should return:
When somebody is plugged in
The state of their battery over time
"""


def parse_date(date):
    if "AM" in date:
        date = date.replace(" AM", "")
        # parse out the hour of the day
        hour = int(date.split(":")[0])
        if hour == 12:
            hour = 0
        minutes = int(date.split(":")[1])
    elif "PM" in date:
        date = date.replace(" PM", "")
        # parse out the hour of the day
        hour = int(date.split(":")[0])
        if hour != 12:
            hour += 12
        minutes = int(date.split(":")[1])
    else:
        return ValueError("Date not in correct format")

    date_minutes = hour * 60 + minutes
    return date_minutes


def simulate_plugin(population_n, std_mins=60):
    df = pd.read_csv("data/EV_Driver_Archetypes.csv")
    # parse "%" strings into floats
    df["Target SoC"] = df["Target SoC"].str.rstrip("%").astype("float") / 100
    df["Plug-in SoC"] = df["Plug-in SoC"].str.rstrip("%").astype("float") / 100
    df["SoC requirement"] = df["SoC requirement"].str.rstrip("%").astype("float") / 100

    # parse date types into datetime and then parse out the hour of the day

    # apply the function to the dataframe
    df["Plug-in time"] = df["Plug-in time"].apply(parse_date)
    df["Plug-out time"] = df["Plug-out time"].apply(parse_date)

    # should make this robust to rounding errors if had time
    df["drivers"] = population_n * df["% of population"] / 100

    # create a df which has a driver id and then 24 columns for each hour of the day, 1 is plugged in 0 is not
    df_schedule = pd.DataFrame(columns=["driver_id", "schedule"])

    # for each group of drivers
    for group in df["Name"].unique():
        # build plug in matrix for each driver
        for i in range(int(df[df.Name == group]["drivers"].values[0])):
            # draw random sample from distribution, std dev is 60 mins
            plug_in_time = np.random.normal(
                df[df.Name == group]["Plug-in time"], std_mins
            )
            # Filter the DataFrame by the 'group' condition
            filtered_df = df[df.Name == group]

            # Calculate the difference between 'Plug-out time' and 'Plug-in time'
            time_difference = filtered_df["Plug-out time"] - filtered_df["Plug-in time"]

            # draw random plug-in duration, need to deel with modulo 24hrs
            if time_difference.values[0] < 0:
                mean_plug_in_duration = time_difference + 24
            else:
                mean_plug_in_duration = time_difference

            # find the implied plug out time
            plug_out_time = plug_in_time + np.random.normal(
                mean_plug_in_duration, std_mins
            )

            # create 24 element array for each driver
            driver_schedule = np.zeros(24)

            plug_in_freq = filtered_df["Plug-in frequency (per day)"]

            if plug_in_freq.values[0] < 1:
                # take a random sample from a uniform distribution
                # if the sample is greater than the plug in frequency, skip the driver
                if np.random.uniform(0, 1) > plug_in_freq.values[0]:
                    continue

            # fill in the array with the plug in and out times
            for j in range(24):
                if plug_out_time < plug_in_time:
                    # because we are dealing with modulo 24hrs
                    if plug_in_time < j * 60 or j * 60 < plug_out_time:
                        driver_schedule[j] = 1
                else:
                    if plug_in_time < j * 60 < plug_out_time:
                        driver_schedule[j] = 1

            # add the driver schedule to the group schedule

            row = pd.DataFrame(
                {
                    "group": [group],
                    "driver_id": [str(i) + f"{uuid.uuid4()}"],
                    "schedule": [driver_schedule],
                    "plug_in_time": [plug_in_time],
                    "plug_out_time": [plug_out_time],
                }
            )

            # Concatenate the new row to the existing df_schedule DataFrame
            df_schedule = pd.concat([df_schedule, row], ignore_index=True)

    # find the avg plug-in schedule

    # Extract the column containing arrays
    arrays = df_schedule["schedule"].values

    # Stack arrays vertically and compute the mean along axis 0
    average_array = np.mean(np.vstack(arrays), axis=0)
    return average_array, df_schedule


# get avg plug in and plug out times
def get_avg_plug_in_out_times(df_schedule):
    avg_plug_in_time = round(df_schedule["plug_in_time"].mean()[0] / 60)
    avg_plug_out_time = round(df_schedule["plug_out_time"].mean()[0] / 60)
    return avg_plug_in_time, avg_plug_out_time


def simulate_charge_path(df_schedule):
    df = pd.read_csv("data/EV_Driver_Archetypes.csv")
    df_charge_path = pd.DataFrame(columns=["driver_id", "charge_path"])

    # for each group of drivers
    for row in df_schedule.iterrows():
        if sum(row[1]["schedule"]) == 0:
            # plug out time
            plug_out_time = row[1]["plug_out_time"]
            # start charge path at rand(1,4) 24hrs after plug out
            charge_path = np.zeros(24)
            plug_out_soc = df[df.Name == group]["Target SoC"].values[0]
            # convert to float from "{}%" string
            plug_out_soc = float(plug_out_soc.strip("%")) / 100
            # get the avergae daily discharge
            avg_daily_discharge = (
                df[df.Name == group]["Miles/yr"].values[0]
                / 365
                / df[df.Name == group]["Efficiency (mi/kWh)"].values[0]
                / df[df.Name == group]["Battery (kWh)"].values[0]
            )
            charge_path[0] = (
                plug_out_soc - round(np.random.uniform(1, 4)) * avg_daily_discharge
            )
            # loop through and drop the avg amount of charge per hour
            for i in range(1, 24):
                charge_path[i] = charge_path[i - 1] - avg_daily_discharge / 24
            # reorder the array
            charge_path = (
                charge_path[24 - round(row[1]["plug_out_time"] / 60) :]
                + charge_path[: 24 - round(row[1]["plug_out_time"] / 60)]
            )
            # add charge path to df_charge_path
            row = pd.DataFrame(
                {
                    "driver_id": [row[1]["driver_id"]],
                    "charge_path": [charge_path],
                }
            )
            df_charge_path = pd.concat([df_charge_path, row], ignore_index=True)
        else:
            # get plug in and out times
            plug_in_time = row[1]["plug_in_time"]
            plug_in_index = int(plug_in_time / 60)
            if plug_in_index > 24:
                plug_in_index = plug_in_index % 24
            plug_out_time = row[1]["plug_out_time"]
            plug_out_index = int(plug_out_time / 60)
            if plug_out_index > 24:
                plug_out_index = plug_out_index % 24
            # get the group plug_in_soc
            group = row[1]["group"]
            plug_in_soc = df[df.Name == group]["Plug-in SoC"].values[0]
            # convert to float from "{}%" string
            plug_in_soc = float(plug_in_soc.strip("%")) / 100
            plug_out_soc = df[df.Name == group]["Target SoC"].values[0]
            # convert to float from "{}%" string
            plug_out_soc = float(plug_out_soc.strip("%")) / 100
            # randomize the plug in soc
            x = np.random.normal(plug_in_soc, 0.05)
            # get the mean discharge, get group miles per year
            mean_discharge_per_day = (
                df[df.Name == group]["Miles/yr"].values[0]
                / 365
                / df[df.Name == group]["Efficiency (mi/kWh)"].values[0]
                / df[df.Name == group]["Battery (kWh)"].values[0]
            )
            # max increase in SoC per Hour (is a drop because we build charge path back to front)
            # max_drop
            max_soc_increase_per_hour = (
                df[df.Name == group]["Charger kW"].values[0]
                / df[df.Name == group]["Battery (kWh)"].values[0]
            )
            # max discharge per hour (70mph/efficiency)/battery size
            max_discharge_per_hour = (
                70 / df[df.Name == group]["Efficiency (mi/kWh)"].values[0]
            ) / df[df.Name == group]["Battery (kWh)"].values[0]
            # charge duration
            charge_duration = plug_out_time - plug_in_time
            if charge_duration < 0:
                charge_duration += 24
            #  min of randomised mean drop or max_soc_increase_per_hour
            # max of min chrge to charge the car and the value
            mean_drop = max(
                min(
                    max_soc_increase_per_hour
                    * np.random.normal(
                        max_soc_increase_per_hour, max_soc_increase_per_hour / 2
                    ),
                    max_soc_increase_per_hour,
                ),
                (plug_out_soc - plug_in_soc / charge_duration),
            )

            std_dev = mean_drop / 3

            # rearrange the array to be in chronological order
            # Rearrange the array to be in chronological order
            schedule = row[1]["schedule"]
            # ensure schedule is a list
            schedule = list(schedule)
            plug_in_index = int(plug_in_index)  # Ensure indices are integers
            plug_out_index = int(plug_out_index)

            # Split the array
            first_part = schedule[plug_in_index:]
            # # 19:24
            second_part = schedule[:plug_in_index]
            # 0:19

            # Combine them to create chrono_array
            chrono_array = first_part + second_part

            # if first part is a 0 then add it to the end of the array
            # NB: sort out the slice ...
            if chrono_array[0] == 0:
                chrono_array = chrono_array[1:] + [0]

            print(chrono_array)

            if plug_out_index < plug_in_index:
                # get the end index of the recentred array
                end_index = int(plug_out_index) + (24 - int(plug_in_index))

            else:
                end_index = plug_out_index

            end_index = end_index % 24

            chrono_array[end_index] = 0.8

            # Initialize the value to be set
            current_value = 0.8

            # Set the values for the rest of the 1s from end_index-1 down to the first 1 index
            for i in range(end_index - 1, -1, -1):
                if current_value - max_soc_increase_per_hour > x:
                    # Generate a drop using normal distribution centered around mean_drop
                    drop = np.random.normal(mean_drop, std_dev)

                    # Ensure the drop does not exceed max_drop and does not make the value go below x
                    drop = min(drop, max_soc_increase_per_hour)
                    drop = max(drop, 0)  # ensure no negative drops

                    # Update current value and set in chrono_array
                    current_value -= drop
                    chrono_array[i] = current_value
                else:
                    # If further drop would go below x, set the first 1 index to x
                    chrono_array[i] = x
                    current_value = chrono_array[i]

            # create discharge cycle from end index to the end of the chrono_array
            for i in range(end_index + 1, 24):
                # Generate a drop using normal distribution centered around mean_drop
                drop = np.random.normal(mean_discharge_per_day, std_dev) / (
                    24 - end_index
                )

                # Ensure the drop does not exceed max_drop and does not make the value go below x
                drop = min(drop, max_discharge_per_hour)
                drop = max(drop, 0)  # ensure no negative drops

                # Update current value and set in chrono_array
                current_value = chrono_array[i - 1] - drop
                chrono_array[i] = current_value

            # return the array to its original order
            chrono_array = (
                chrono_array[int(24 - plug_in_index) :]
                + chrono_array[: int(24 - plug_in_index)]
            )
            # Ensure all elements are floats
            chrono_array = [
                float(x) if isinstance(x, (int, float)) else float(x[0])
                for x in chrono_array
            ]

            # Convert to np.array
            chrono_array = np.array(chrono_array)
            # add chrono array to df_charge_path
            row = pd.DataFrame(
                {
                    "driver_id": [row[1]["driver_id"]],
                    "charge_path": [chrono_array],
                }
            )
            df_charge_path = pd.concat([df_charge_path, row], ignore_index=True)

    # save the charge path to a csv
    df_charge_path.to_csv("data/charge_path.csv")

    # averge the charge path
    arrays = df_charge_path["charge_path"].values
    average_array = np.mean(np.vstack(arrays), axis=0)
    # get 95th percentile
    percentile_95 = np.percentile(np.vstack(arrays), 95, axis=0)
    # get 5th percentile
    percentile_5 = np.percentile(np.vstack(arrays), 5, axis=0)
    return average_array, percentile_95, percentile_5


def create_img(population_size, std_mins):
    plt.rcParams["figure.figsize"] = [7.50, 3.50]
    plt.rcParams["figure.autolayout"] = True
    # get the average schedule
    avg_schedule, df_schedule = simulate_plugin(population_size, std_mins)
    # get the charge path
    average_array, percentile_95, percentile_5 = simulate_charge_path(df_schedule)
    avg_plug_in_time, avg_plug_out_time = get_avg_plug_in_out_times(df_schedule)
    print(average_array)
    # plt these percentiles on another y axis
    fig, ax = plt.subplots()
    ax.plot(range(24), 100 * np.array(average_array), label="Average", color="blue")
    ax.fill_between(
        range(24),
        100 * np.array(percentile_5),
        100 * np.array(percentile_95),
        color="blue",
        alpha=0.2,
        label="5th-95th percentile",
    )
    ax.set_xlabel("Hour of the day")
    ax.set_ylabel("SoC %, mean and 5-9th Percentile", color="blue")
    # plot horizontal lines at avg plug in and out times
    ax.axvline(
        avg_plug_in_time, color="black", linestyle="--", label="Avg plug in time"
    )
    ax.axvline(
        avg_plug_out_time, color="black", linestyle="--", label="Avg plug out time"
    )
    ax2 = ax.twinx()
    # plot a bar chart from the average schedule on ax2
    ax2.bar(
        range(24), 100 * np.array(avg_schedule), alpha=0.2, color="red", label="Average"
    )
    ax2.set_ylabel("% of EVs plugged in")
    img_buf = io.BytesIO()
    plt.savefig(img_buf, format="png")
    plt.close()
    return img_buf


# Result page route using path parameters
@app.get("/result/{population_size}/{std_mins}", response_class=HTMLResponse)
async def get_img(
    background_tasks: BackgroundTasks, population_size: int, std_mins: int
):
    img_buf = create_img(population_size, std_mins)
    # get the entire buffer content
    # because of the async, this will await the loading of all content
    bufContents: bytes = img_buf.getvalue()
    background_tasks.add_task(img_buf.close)
    headers = {"Content-Disposition": 'inline; filename="out.png"'}
    return Response(bufContents, headers=headers, media_type="image/png")
