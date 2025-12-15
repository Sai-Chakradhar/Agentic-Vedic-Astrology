import json
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder
from jyotishyamitra import input_birthdata, generate_astrologicalData, set_output, validate_birthdata, get_birthdata
import datetime

def get_lat_lon(city_name):
    """
    Resolves city name to latitude, longitude and timezone.
    """
    geolocator = Nominatim(user_agent="astrology_app")
    location = geolocator.geocode(city_name)
    
    if not location:
        return None, None, None
        
    lat = location.latitude
    lon = location.longitude
    
    tf = TimezoneFinder()
    timezone_str = tf.timezone_at(lng=lon, lat=lat)
    
    return lat, lon, timezone_str

def get_chart_data(name, dob_str, time_str, city_name):
    """
    Generates Vedic Astrology chart data using jyotishyamitra.
    dob_str: YYYY-MM-DD
    time_str: HH:MM
    """
    lat, lon, timezone_str = get_lat_lon(city_name)
    if not lat:
        return {"error": f"Could not find location: {city_name}"}

    # Parse date and time
    try:
        dt_date = datetime.datetime.strptime(dob_str, "%Y-%m-%d")
        dt_time = datetime.datetime.strptime(time_str, "%H:%M")
    except ValueError as e:
        return {"error": f"Invalid date/time format: {e}"}

    # jyotishyamitra input format: 
    # (name, gender, day, month, year, hour, min, sec, lat, lon, timezone_str)
    # Gender is required but not critical for planetary pos, defaulting to 'unknown'
    
    # Note: jyotishyamitra might expect timezone as offset or string. 
    # Let's check the library usage or assume it handles standard inputs. 
    # Based on general usage, it often takes detailed inputs.
    
    # Let's try to capture the output file
    output_filename = f"{name}_chart.json"
    
    # Input data
    # format: input_birthdata(name, gender, day, month, year, hour, min, sec, place, lat, lon, timezone)
    # Timezone often needs to be +5.5 format for some libs, but let's see. 
    # If the library takes a string timezone, great. If it needs offset, we need to calculate.
    
    # Calculate offset
    import pytz
    tz = pytz.timezone(timezone_str)
    # Arbitrary date for offset calculation (using birth date)
    local_dt = tz.localize(datetime.datetime(dt_date.year, dt_date.month, dt_date.day))
    offset_seconds = local_dt.utcoffset().total_seconds()
    offset_hours = offset_seconds / 3600.0
    
    # jyotishyamitra 1.3+ likely takes arguments.
    # We will wrap this in a try-except block and print what we get.
    
    try:
        birthdata = input_birthdata(
            name=name,
            gender="male", 
            day=dt_date.day,
            month=dt_date.month,
            year=dt_date.year,
            hour=dt_time.hour,
            min=dt_time.minute,
            sec=0,
            place=city_name,
            lattitude=lat,
            longitude=lon,
            timezone=offset_hours 
        )
        
        if validate_birthdata() != "SUCCESS":
             return {"error": "Birth data validation failed."}
             
        # Get cleaned birthdata
        bd = get_birthdata()
             
        # Set output
        # Using current directory for simplicity, using safe filename
        safe_name = "".join(x for x in name if x.isalnum())
        set_output(".", safe_name)
        
        # Generate data
        output_path = generate_astrologicalData(bd)
        
        # Hack to handle the way library constructs path with backslash on non-windows
        # It seems it joins dir + "\\" + name + ".json"
        # If output_path exists, use it. If not, try to account for the backslash in filename.
        import os
        final_path = output_path
        if not os.path.exists(final_path):
             # Try to find the file if it has a backslash in name
             possible_name = f".\\{safe_name}.json"
             if os.path.exists(possible_name):
                 final_path = possible_name
        
        if not os.path.exists(final_path):
             return {"error": f"Output file not found at {output_path} or {final_path}"}
             
        with open(final_path, 'r') as f:
            data = json.load(f)
            
        # Clean up
        try:
            os.remove(final_path)
        except:
            pass
            
        return data
    except Exception as e:
        import traceback
        return {"error": f"Astrology calculation failed: {str(e)}\n{traceback.format_exc()}"}

if __name__ == "__main__":
    # Test run
    result = get_chart_data("TestUser", "1990-01-01", "12:00", "New Delhi")
    with open("test_run.json", "w") as f:
        json.dump(result, f, indent=2)
    print("Test run complete. Saved to test_run.json")
