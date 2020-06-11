import copy
import ephem
import jdatetime
import json
import math
import os
import utm

from datetime import timedelta


BASE_DIR = os.path.dirname(os.path.realpath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
ACCIDENT_FILE_PATH = os.path.join(DATA_DIR, 'accidents.tsv')
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')
GEOJSON_FILE_PATH = os.path.join(OUTPUT_DIR, 'out.geojson')
TEHRAN_AVERAGE_ELEVATION = 1189  # meters
TEHRAN_TO_UTC = timedelta(hours=4, minutes=30)


def _get_datetime(date, time, year_month):
    if date and time:
        if len(date) == 8:
            year = int(date.strip()[:4])
            month = int(date.strip()[4:6])
        else:
            year = int(year_month.split('.')[0])
            month = int(year_month.split('.')[1])
        day = int(date.strip()[-2:])
        if len(time) < 4:
            time = '0' * (4 - len(time)) + time
        hour = int(time[:2])
        minute = int(time[2:])
        return jdatetime.datetime(year, month, day, hour, minute).togregorian()
    return None


def _get_light(datetime, lat, long):
    """
    https://stackoverflow.com/questions/43299500/pandas-convert-datetime-timestamp-to-whether-its-day-or-night
    https://www.timeanddate.com/astronomy/different-types-twilight.html
    """
    if datetime:
        sun = ephem.Sun()
        observer = ephem.Observer()
        observer.lat, observer.lon, observer.elevation = lat, long, TEHRAN_AVERAGE_ELEVATION
        observer.date = datetime - TEHRAN_TO_UTC
        sun.compute(observer)
        current_sun_alt = sun.alt
        angle = current_sun_alt * 180 / math.pi
        if 0 < angle:
            return 'day'
        elif -6 < angle < 0:
            return 'civil'
        elif -12 < angle < -6:
            return 'nautical'
        elif -18 < angle < -12:
            return 'astronomical'
        else:
            return 'night'
    return None


def _simple_light(light):
    if light == 'civil' or light == 'nautical' or light == 'astronomical':
        return 'twilight'
    else:
        return light


def _clean_age(age):
    if age:
        return int(age)
    return None


def _clean_vehicle(vehicle):
    vehicle = vehicle.strip()
    if vehicle in ['سواري', 'سواری', 'راننده خودرو', 'سرنشین خودرو']:
        return 'car'
    elif vehicle == 'آمبولانس':
        return 'ambulance'
    elif vehicle == 'دوچرخه':
        return 'bike'
    elif vehicle == 'وانت بار':
        return 'pickup_truck'
    elif vehicle in ['موتورسيکلت', 'سرنشین موتور', 'راکب موتور']:
        return 'motorcycle'
    elif vehicle in ['کاميون', 'کاميونت']:
        return 'truck'
    elif vehicle in ['عابر', 'عابر پیاده']:
        return 'pedestrian'
    elif vehicle == 'ميني بوس':
        return 'mini_bus'
    elif vehicle in ['تريلر', 'تريلي']:
        return 'trailer'
    elif vehicle == 'اتوبوس':
        return 'bus'
    elif vehicle == 'میکسر':
        return 'cement_mixer'
    return 'other'


def _simple_vehicle(clean_vehicle):
    if clean_vehicle not in ['car', 'bike', 'motorcycle', 'pedestrian']:
        return 'heavy'
    return clean_vehicle


def _clean_gender(gender):
    if int(gender) == 1:
        return 'man'
    else:
        return 'woman'


def _data_generator():
    with open(ACCIDENT_FILE_PATH, 'r') as accident_file:
        for i, line in enumerate(accident_file.readlines()):
            if i > 0:  # skip header
                split_line = line.strip().split('\t')
                if len(split_line) == 54:
                    gender = _clean_gender(split_line[3])
                    age = _clean_age(split_line[4])
                    date = split_line[17]
                    time = split_line[18]
                    year_month = split_line[47]
                    datetime = _get_datetime(date, time, year_month)
                    vehicle_deceased = _simple_vehicle(_clean_vehicle(split_line[29]))
                    vehicle_killer = _simple_vehicle(_clean_vehicle(split_line[36]))
                    accident_reason = split_line[44].strip()
                    utm_x = int(float(split_line[50]))
                    utm_y = int(float(split_line[51]))
                    lat, long = utm.to_latlon(utm_x, utm_y, 39, 'S')
                    light = _simple_light(_get_light(datetime, lat, long))
                    yield {
                        'gender': gender,
                        'age': age,
                        'datetime': datetime,
                        'vehicle_deceased': vehicle_deceased,
                        'vehicle_killer': vehicle_killer,
                        'accident_reason': accident_reason,
                        'utm_x': utm_x,
                        'utm_y': utm_y,
                        'lat': lat,
                        'long': long,
                        'light': light,
                    }


def run():
    features = []
    for entry in _data_generator():
        modified_entry = copy.deepcopy(entry)
        del modified_entry['lat'], modified_entry['long']
        if modified_entry['datetime']:
            modified_entry['datetime'] = modified_entry['datetime'].strftime("%Y-%m-%d %H:%M:%S")
        features.append({
            'type': 'Feature',
            'geometry': {
                'type': 'Point',
                'coordinates': [entry['long'], entry['lat']],
            },
            'properties': modified_entry,
        })
    with open(GEOJSON_FILE_PATH, 'w') as geojson_file:
        geojson_file.write(json.dumps(
            {
                'type': 'FeatureCollection',
                'features': features,
            }
        ))


if __name__ == "__main__":
    run()
