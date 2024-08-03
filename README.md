# A notification server that sends notifications to Google Home

This is pretty simple. I had started using [noelportugal's really great node Google Home Notifier](https://github.com/noelportugal/google-home-notifier) but was having some issues with stability. 

I decided to write it in a language i know a bit better - python! yay. Python is your friend. 

The gist is this: 

This is a webservice that has two endpoints:

- /trigger_alarm
- /health

# use

## getting started

```bash
docker network create -d macvlan \
  --subnet=192.168.70.0/24 \
  --gateway=192.168.70.1 \
  -o parent=eno1 \
  chromecast_net
```

This uses flask and you should just be able to install the requirements: `pip install -r requirements.txt` and then run the webservice `python main.py`

You will have to edit `main.py` and change the `device_name` to one of your google home device's name. If you have more than 1 google home, I would recommend you put all your google homes into a play group and place the play groups name in the `device_name` variable. 


## Running for real

I use docker to run it. It works pretty well. I even included some pretty good docker script that will make it easier. Please check that out for more help. 

# How

Google homes are just chromecasts! Who knew! You just have to treat them like chromecasts. They show up when you browse for chromecasts via python or any other code library. You can then just send audio their way. 
