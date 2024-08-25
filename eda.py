# create pairplot of the EV_Driver_Archetypes.csv Data

import pandas as pd
import numpy as np

import seaborn as sns
import matplotlib.pyplot as plt
import io
import matplotlib
import uuid

df = pd.read_csv("data/EV_Driver_Archetypes.csv")
# parse "%" strings into floats
df["Target SoC"] = df["Target SoC"].str.rstrip("%").astype("float") / 100
df["Plug-in SoC"] = df["Plug-in SoC"].str.rstrip("%").astype("float") / 100
df["SoC requirement"] = df["SoC requirement"].str.rstrip("%").astype("float") / 100


# parse date types into datetime and then parse out the hour of the day
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


# apply the function to the dataframe
df["Plug-in time"] = df["Plug-in time"].apply(parse_date)
df["Plug-out time"] = df["Plug-out time"].apply(parse_date)


# sns.pairplot(df)
# # make it fit the screen
# plt.tight_layout()
# plt.savefig("static/pairplot.png")


# boot strap individual data points from the EV_Driver_Archetypes.csv Data
def bootsrap_data(n, feature, mean, std):
    # create empty dataframe with n rows and column name feature
    df_boot = pd.DataFrame(columns=[feature])

    # pull n random samples from the normal distribution
    samples = np.random.normal(mean, std, n)

    # add the samples to the dataframe
    df_boot[feature] = samples
    return df_boot


df_plug = bootsrap_data(
    10, "Plug-in SoC", df[df.Name == "Average (UK)"]["Plug-in SoC"], 0.1
)
df_charge_dur = bootsrap_data(
    10,
    "Charging duration (hrs)",
    df[df.Name == "Average (UK)"]["Charging duration (hrs)"],
    10,
)

population = 1_000
# should make this robust to rounding errors if had time
df["drivers"] = population * df["% of population"] / 100

# create a result dataframe
df_result = pd.DataFrame(columns=["Name", "Plug-in time", "Plug-out time", "driver_id"])
# create a df which has a driver id and then 24 columns for each hour of the day, 1 is plugged in 0 is not
df_schedule = pd.DataFrame(columns=["driver_id", "schedule"])

# for each group of drivers
for group in df["Name"].unique():
    # build plug in matrix for each driver
    for i in range(int(df[df.Name == group]["drivers"].values[0])):
        # draw random sample from distribution, std dev is 60 mins
        plug_in_time = np.random.normal(df[df.Name == group]["Plug-in time"], 60)
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
        plug_out_time = plug_in_time + np.random.normal(mean_plug_in_duration, 60)

        # create 24 element array for each driver
        driver_schedule = np.zeros(24)
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

# save the schedule to a csv to review
df_schedule.to_csv("data/schedule.csv")

# find the avg plug-in schedule

# Extract the column containing arrays
arrays = df_schedule["schedule"].values

# Stack arrays vertically and compute the mean along axis 0
average_array = np.mean(np.vstack(arrays), axis=0)

print(average_array)

# charge/discharge path

for row in df_schedule.iterrows():
    driver = row[1]
    driver_id = driver["driver_id"]
    schedule = driver["schedule"]
    plug_in_time = driver["plug_in_time"]
    plug_out_time = driver["plug_out_time"]
    time_difference = plug_out_time - plug_in_time
    if time_difference < 0:
        time_difference += 24
    # get random plug-in soc
    group = driver["group"]
    target_soc = np.random.normal(df[df.Name == group]["Target SoC"], 0.1)
    soc_requirement = np.random.normal(df[df.Name == group]["SoC requirement"], 0.1)

    # charge/discharge path
    if plug_out_time < plug_in_time:
        charge_path = np.zeros(24)
        for i in range(24):
            if schedule[i] == 1:
                charge_path[i] = df[df.Name == group]["Plug-in SoC"]
            else:
                charge_path[i] = df[df.Name == group]["Target SoC"]
