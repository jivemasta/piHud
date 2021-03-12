#piHud Main file
#this will display bitcoin price, weather, and tindie orders on a eInk display on a raspberry pi

import os
import platform
import requests
import json
import time
import threading
from PIL import Image, ImageDraw, ImageFont
import logging

#check if we are running on linux so we can be cross platform friendly since inky library doesn't work on windows
#on windows we just make a RGB image and output it
linux = platform.system() != "Windows"

#keep inky code behind if statements so that it will run on windows for development
if linux:
    from inky import InkyWHAT

#setup of debug logging
logging.basicConfig(level=logging.DEBUG,format='[%(asctime)s][%(levelname)s] (%(threadName)-10s) %(message)s',)

ticks = 0
btcPrice = {}
tindieOrders = []
weather = {}
tindieApiUser = ''
tindieApiKey = ''
weatherApiKey = ''

if linux:
    inkyBoard  = InkyWHAT('red')

def GetSettingsFile():
    #open settings file, it's just a file with a json object with api key data

    global tindieApiUser
    global tindieApiKey
    global weatherApiKey

    #get the config file from the same directory as the script file
    loc = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))

    #open the config file and read the private keys
    f = open(os.path.join(loc,"config.cfg"), "r")
    fileStr = f.read()
    settings = json.loads(fileStr)

    tindieApiUser = settings['tindieApiUser']
    tindieApiKey = settings['tindieApiKey']
    weatherApiKey = settings['weatherApiKey']

def GetBTCPrice():
    #get bitcoin price data from gemini API, can handle up to 1 call per second, but we won't update that fast
    logging.debug('Getting BTC Price')

    global btcPrice

    #If we ever want to change which crypto to get. V2?
    symbol = 'BTCUSD'

    #get ticker data, gets data for the last 24 hours. Open, close, high, low. Close is most current price
    bitcoinApiUrl = f"https://api.gemini.com/v2/ticker/{symbol}"
    btcResponse = requests.get(bitcoinApiUrl)
    btcResponseJson = btcResponse.json()
    btcPrice = btcResponse.json()

    logging.debug('Done Getting BTC Price')

def GetTindieOrders():
    logging.debug("Getting Tindie Orders")

    global tindieOrders
    global tindieApiUser
    global tindieApiKey

    #API Key info for tindie account

    tindieApiUrl = "/api/v1/order/?format=json&username=" + tindieApiUser + "&api_key=" + tindieApiKey

    #Variables
    orderList = []
    moreOrders = True

    #loops through api calls until it gets to the end of the list adding each batch to the orderList
    #will go through at least once to get list, then check the meta object to see if there is a URL to the next list
    while moreOrders == True:
        #starts with the base API URL, but will get updated to the next list URL at the end of each loop
        tindieResponse = requests.get('https://www.tindie.com' + tindieApiUrl,{'limit':'50'})

        #Convert response to JSON Object and add orders to orderList
        tindieJSON = tindieResponse.json()
        orderList +=  tindieJSON['orders']

        #The API adds a URL to the next chunk of the order list in the meta object
        #If it has something, make that the next API URL and loop around, otherwise leave the loop
        if tindieJSON['meta']['next'] != None:
            moreOrders = True
            tindieApiUrl = tindieJSON['meta']['next']
        else:
            moreOrders = False
    #return the entire list of orders
    tindieOrders = orderList

    logging.debug("Done Getting Tindie Orders")

def GetWeather():
    #for JSON structure
    #https://openweathermap.org/api/one-call-api

    logging.debug('Getting Weather')

    global weather
    global weatherApiKey

    #lat and lon for the house
    lat = 41.060488965115056
    lon = -83.7288217363699
    units = 'imperial'

    #set up API URL
    weatherApiUrl = f'https://api.openweathermap.org/data/2.5/onecall?lat={lat}&lon={lon}&units={units}&appid={weatherApiKey}'

    #get weather as a JSON object
    weatherResponse = requests.get(weatherApiUrl)

    weather = weatherResponse.json()

    logging.debug('Done Getting Weather')

def UpdateData():
    global btcPrice
    global tindieOrders

    btcThread = threading.Thread(target=GetBTCPrice)
    tindieThread = threading.Thread(target=GetTindieOrders)
    weatherThread = threading.Thread(target=GetWeather)

    btcThread.start()
    tindieThread.start()
    weatherThread.start()

    btcThread.join()
    tindieThread.join()
    weatherThread.join()

def RenderImage():
    global btcPrice

    #set default colors on windows we use RGB, on linux we use the inky colors
    white = (255,255,255) if not linux else inkyBoard.WHITE
    black = (0,0,0) if not linux else inkyBoard.BLACK
    red = (255,0,0) if not linux else inkyBoard.RED

    #create a new image file to put on the display
    #display is 400x300 with 3 colors white, red, and black
    if linux:
        out = Image.new('P',(400,300))
    else:
        out = Image.new('RGB',(400,300),(255,255,255))
    #load default font
    fontLarge = ImageFont.truetype('arial.ttf',size=40)
    fontSmall = ImageFont.truetype('arial.ttf',size=20)
    #create the drawing object
    draw = ImageDraw.Draw(out)

    #get bitcoin data
    btcOpen = float(btcPrice['open'])
    btcClose = float(btcPrice['close'])
    btcHigh = float(btcPrice['high'])
    btcLow = float(btcPrice['low'])

    #draw bitcoin data
    #bitcoin price will be red if current price is lower than the open, and black if higher than open
    draw.text((0,0),f'{btcClose:.2f}',fill=black if btcClose > btcOpen else red,font=fontLarge)
    draw.text((0,40),f'Open:{btcOpen:.2f}',fill=black,font=fontSmall)
    draw.text((0,60),f'High:{btcHigh:.2f}',fill=black,font=fontSmall)
    draw.text((0,80),f'Low:{btcLow:.2f}',fill=black,font=fontSmall)

    #draw weather
    temp = weather['current']['temp']
    #draw.text((0,30),f'Temp: {temp}',fill=black,font=font)

    unshippedOrders = 0
    for order in tindieOrders:
        if order['shipped'] == False:
            unshippedOrders +=1
    #draw.text((0,60),f'Unshipped Orders: {unshippedOrders}',fill=black,font=font)

    if not linux:
        out.show()

    if linux:
        inkyBoard.set_image(out)
        inkyBoard.show()

#Start the actual program by getting settings, and entering the main loop
GetSettingsFile()

while(1):
    #update all the data first
    #this is a threaded function that will update everything at the same time, but won't finish until everything is done
    UpdateData()

    #create the image that will display on the eInk screen
    RenderImage()

    #update at a set interval
    time.sleep(60)