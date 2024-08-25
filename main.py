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


# boot strap individual data points from the EV_Driver_Archetypes.csv Data
def bootsrap_data(n, feature, mean, std):
    # create empty dataframe with n rows and column name feature
    df_boot = pd.DataFrame(columns=[feature])

    # pull n random samples from the normal distribution
    samples = np.random.normal(mean, std, n)

    # add the samples to the dataframe
    df_boot[feature] = samples
    return df_boot


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
    return average_array


def create_img(population_size, std_mins):
    plt.rcParams["figure.figsize"] = [7.50, 3.50]
    plt.rcParams["figure.autolayout"] = True
    # get the average schedule
    avg_schedule = simulate_plugin(population_size, std_mins)
    # plot a bar chart from the average schedule
    plt.bar(range(24), avg_schedule)
    plt.xlabel("Hour of the day")
    plt.ylabel("Fraction of population plugged in")
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
