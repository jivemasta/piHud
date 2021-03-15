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
ethPrice = {}
tindieOrders = []
weather = {}
tindieApiUser = ''
tindieApiKey = ''
weatherApiKey = ''

#get the config file from the same directory as the script file
loc = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))

if linux:
    inkyBoard  = InkyWHAT('red')

def GetSettingsFile():
    #open settings file, it's just a file with a json object with api key data

    global tindieApiUser
    global tindieApiKey
    global weatherApiKey

    #open the config file and read the private keys
    f = open(os.path.join(loc,"config.cfg"), "r")
    fileStr = f.read()
    settings = json.loads(fileStr)

    tindieApiUser = settings['tindieApiUser']
    tindieApiKey = settings['tindieApiKey']
    weatherApiKey = settings['weatherApiKey']

def GetCryptoPrice():
    #get bitcoin price data from gemini API, can handle up to 1 call per second, but we won't update that fast
    logging.debug('Getting Crypto Price')

    global btcPrice
    global ethPrice

    #If we ever want to change which crypto to get. V2?
    symbol = 'BTCUSD'

    #get ticker data, gets data for the last 24 hours. Open, close, high, low. Close is most current price
    cryptoApiUrl = f"https://api.gemini.com/v2/ticker/{symbol}"
    cryptoResponse = requests.get(cryptoApiUrl)
    btcPrice = cryptoResponse.json()

    symbol = 'ETHUSD'

    cryptoApiUrl = f"https://api.gemini.com/v2/ticker/{symbol}"
    cryptoResponse = requests.get(cryptoApiUrl)
    ethPrice = cryptoResponse.json()


    logging.debug('Done Getting Crypto Price')

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

    cryptoThread = threading.Thread(target=GetCryptoPrice)
    tindieThread = threading.Thread(target=GetTindieOrders)
    weatherThread = threading.Thread(target=GetWeather)

    cryptoThread.start()
    tindieThread.start()
    weatherThread.start()

    cryptoThread.join()
    tindieThread.join()
    weatherThread.join()

def RenderImage():
    global btcPrice
    global ethPrice
    global weather

    #create a new image file to put on the display
    #display is 400x300 with 3 colors white, red, and black
    # if linux:
    #     out = Image.new('P',(400,300))
    # else:
    #     out = Image.new('RGB',(400,300),(255,255,255))

    #create the output image
    #set a palette to be 3 colors, white = 0, black = 1, red = 2
    out = Image.new('P',(400,300))
    out.putpalette((255, 255, 255, 0, 0, 0, 255, 0, 0) + (0, 0, 0) * 252)

    #load fonts
    fontLarge = ImageFont.truetype('arial.ttf',size=32)
    fontSmall = ImageFont.truetype('arial.ttf',size=16)

    #set default colors on windows we use RGB, on linux we use the inky colors
    white = 0 if not linux else inkyBoard.WHITE
    black = 1 if not linux else inkyBoard.BLACK
    red = 2 if not linux else inkyBoard.RED

    #set line thickness
    lineThickness = 2
    #create the drawing object
    draw = ImageDraw.Draw(out)

    #draw framing lines
    draw.line([(200,0),(200,80)],fill=black,width=lineThickness)
    draw.line([(0,80),(400,80)],fill=black,width=lineThickness)
    draw.line([(0,112),(400,112)],fill=black,width=lineThickness)

    #get bitcoin data
    btcOpen = float(btcPrice['open'])
    btcClose = float(btcPrice['close'])
    btcHigh = float(btcPrice['high'])
    btcLow = float(btcPrice['low'])

    #draw bitcoin data
    #bitcoin price will be red if current price is lower than the open, and black if higher than open
    draw.text((32,0),f'{btcClose:.2f}',fill=black if btcClose > btcOpen else red,font=fontLarge)
    draw.text((5,32),f'Open:{btcOpen:.2f}',fill=black,font=fontSmall)
    draw.text((5,48),f'High:{btcHigh:.2f}',fill=black,font=fontSmall)
    draw.text((5,64),f'Low:{btcLow:.2f}',fill=black,font=fontSmall)

    #draw bitcoin logo
    btcLogo = Image.open(os.path.join(loc, "img/Bitcoin.png"))
    btcLogo = btcLogo.convert("RGB").quantize(palette=out)
    out.paste(btcLogo,(0,0))

    #get ethereum data
    ethOpen = float(ethPrice['open'])
    ethClose = float(ethPrice['close'])
    ethHigh = float(ethPrice['high'])
    ethLow = float(ethPrice['low'])

    #draw ethereum data
    draw.text((241,0),f'{ethClose:.2f}',fill=black if ethClose > ethOpen else red,font=fontLarge)
    draw.text((206,32),f'Open:{ethOpen:.2f}',fill=black,font=fontSmall)
    draw.text((206,48),f'High:{ethHigh:.2f}',fill=black,font=fontSmall)
    draw.text((206,64),f'Low:{ethLow:.2f}',fill=black,font=fontSmall)

    #draw eth logo
    ethLogo = Image.open(os.path.join(loc, "img/eth.png"))
    ethLogo = ethLogo.convert("RGB").quantize(palette=out)
    out.paste(ethLogo,(209,0))

    #draw weather
    temp = weather['current']['temp']
    condition = weather['current']['weather'][0]['description']
    draw.text((0,80),f'Temp: {temp} | {condition}',fill=black,font=fontLarge)

    #get unshipped orders and print each one out
    unshippedOrders = 0
    for order in tindieOrders:
        itemcount = 0
        if order['shipped'] == False:
            unshippedOrders +=1
            country = order['shipping_country']
            for item in order['items']:
                itemcount+=1
            draw.text((0,96+(unshippedOrders*16)),f'Ship {itemcount} item(s) to {country}',fill=black,font=fontSmall)

    #show picture in windows photo viewer
    if not linux:
        out.show()

    #update inky display
    if linux:
        out = out.rotate(180)
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