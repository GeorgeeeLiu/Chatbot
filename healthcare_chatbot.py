from __future__ import unicode_literals

import os
import sys
import redis
import requests
from bs4 import BeautifulSoup

from argparse import ArgumentParser

from flask import Flask, request, abort
from linebot import (
    LineBotApi, WebhookParser
)
from linebot.exceptions import (
    InvalidSignatureError
)

from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, ImageMessage, VideoMessage, FileMessage, StickerMessage,
    StickerSendMessage, ImageSendMessage, PostbackTemplateAction, ImageCarouselTemplate,
    CarouselColumn, ImageCarouselColumn, URITemplateAction,URIImagemapAction, TemplateSendMessage, ImagemapArea,
    CarouselTemplate, FollowEvent, MessageTemplateAction,
    ButtonsTemplate, JoinEvent, LeaveEvent
)
from linebot.utils import PY3

app = Flask(__name__)
# get channel_secret and channel_access_token from your environment variable
channel_secret = os.getenv('LINE_CHANNEL_SECRET', None)
channel_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', None)
# obtain the port that heroku assigned to this app.
heroku_port = os.getenv('PORT', None)
if channel_secret is None:
    print('Specify LINE_CHANNEL_SECRET as environment variable.')
    sys.exit(1)
if channel_access_token is None:
    print('Specify LINE_CHANNEL_ACCESS_TOKEN as environment variable.')
    sys.exit(1)

line_bot_api = LineBotApi(channel_access_token)
parser = WebhookParser(channel_secret)

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # parse webhook body
    try:
        events = parser.parse(body, signature)
    except InvalidSignatureError:
        abort(400)

    # if event is MessageEvent and message is TextMessage, then echo text
    for event in events:
        if not isinstance(event, MessageEvent):
            continue
        if isinstance(event.message, TextMessage):
            handle_TextMessage(event)
        if isinstance(event.message, ImageMessage):
            handle_ImageMessage(event)
        if isinstance(event.message, VideoMessage):
            handle_VideoMessage(event)
        if isinstance(event.message, FileMessage):
            handle_FileMessage(event)
        if isinstance(event.message, StickerMessage):
            handle_StickerMessage(event)

        if not isinstance(event, MessageEvent):
            continue
        if not isinstance(event.message, TextMessage):
            continue

    return 'OK'

def prepareTitle(text):
    result = text[:37] + "..." if len(text) > 40 else text
    result = "{}".format(result)
    return result
def report():
    res = requests.get('https://www.who.int/emergencies/diseases/novel-coronavirus-2019/situation-reports')
    soup = BeautifulSoup(res.text, 'html.parser')
    sreport = soup.find_all('a', attrs={'target': '_blank'})[5]
    report = str('https://www.who.int' + sreport['href'])
    return report

def getNews():
    result = []
    res = requests.get('https://www.who.int/emergencies/diseases/novel-coronavirus-2019')
    soup = BeautifulSoup(res.text, 'html.parser')
    news = soup.find_all('a', {'class': 'link-container'}, limit=5)

    for t in news:
        value = t.attrs
        title = prepareTitle(value['aria-label'])
        url = value['href']
        column = CarouselColumn(
            title=title,
            text=' ',
            actions=[URITemplateAction(
                    label='More',
                    uri=url
                )
            ]
        )
        result.append(column)

    carousel = TemplateSendMessage(
        alt_text="5 latest news",
        template=CarouselTemplate(
            columns=result
        )
    )
    result_text = 'Find more information about coronavirus, please click: https://www.who.int/emergencies/diseases/novel-coronavirus-2019 '
    result = [carousel, TextSendMessage(text=result_text)]
    return result

def getMythBusters():
    result = []
    res = requests.get(
        'https://www.who.int/emergencies/diseases/novel-coronavirus-2019/advice-for-public/myth-busters')
    soup = BeautifulSoup(res.text, 'html.parser')
    myths = soup.find('div', attrs={'id': 'PageContent_C003_Col01'})
    for num in range(1, 6):
        # myths1 = myths.select('h2')[num + 1]
        myths_image = myths.select('.link-container')[num]
        # title = myths1.text
        url = myths_image['href']
        column = ImageCarouselColumn(
            image_url=str(url),
            action=URITemplateAction(label='Details', uri=url))
        result.append(column)
    carousel = TemplateSendMessage(
        alt_text="5 myth busters",
        template=ImageCarouselTemplate(
            columns=result
        )
    )
    result_text = 'Find more information about myth busters, please click: https://www.who.int/emergencies/diseases/novel-coronavirus-2019/advice-for-public/myth-busters '
    result = [carousel, TextSendMessage(text=result_text)]
    return result

def MainMenu():
    buttons_template = ButtonsTemplate(text='Main services', actions=[
        MessageTemplateAction(label='Popular science', text='Popular science'),
        MessageTemplateAction(label='Outbreak News', text='News about COVID-2019'),
        MessageTemplateAction(label='Emergency & Services', text='Emergency & Services'),
    ])
    template_message = TemplateSendMessage(
        alt_text='Menu', template=buttons_template)
    return template_message

def Menu2():
    buttons_template = ButtonsTemplate(text='News about COVID-2019', actions=[
        MessageTemplateAction(label='Situation report', text='Situation report'),
        MessageTemplateAction(label='Latest News', text='Latest news'),
        MessageTemplateAction(label='Myth busters', text='Myth busters'),
        MessageTemplateAction(label='Main Menu', text='Menu'),
    ])
    template_message = TemplateSendMessage(
        alt_text='Menu', template=buttons_template)
    return template_message

# Handler function for Text Message
def handle_TextMessage(event):
    print(event.message.text)
    if event.message.text == 'Menu':
        msg = 'This is main menu '
        menu = MainMenu()
        line_bot_api.reply_message(
            event.reply_token, [
                TextSendMessage(msg),
                menu]
        )
    elif event.message.text == 'Popular science':
        msg = 'This is popular Science knowledge'
        menu = MainMenu()  # Menu1()
        line_bot_api.reply_message(
            event.reply_token, [
                TextSendMessage(msg),
                menu]
        )
    elif event.message.text == 'News about COVID-2019':
        msg = 'Hello! This is the latest news about COVID-2019, what kinds of information you want to know? '
        menu = Menu2()
        line_bot_api.reply_message(
            event.reply_token, [
                TextSendMessage(msg),
                menu]
        )
    elif event.message.text == 'Situation report':
        msg1 = 'This is the latest situation report, please click:' + report()
        msg2 = 'Find more reports please click: https://www.who.int/emergencies/diseases/novel-coronavirus-2019/situation-reports'
        line_bot_api.reply_message(
            event.reply_token, [
                TextSendMessage(msg1),
                TextSendMessage(msg2)]
        )

    elif event.message.text == 'Latest news':
        line_bot_api.reply_message(
            event.reply_token, getNews())

    elif event.message.text == 'Myth busters':
        # kkk = ImageSendMessage(
        #       original_content_url='https://www.who.int/docs/default-source/coronaviruse/20200312-sitrep-52-covid-19.pdf?sfvrsn=e2bfc9c0_2',
        #       preview_image_url='https://www.who.int/docs/default-source/coronaviruse/20200312-sitrep-52-covid-19.pdf?sfvrsn=e2bfc9c0_2'
        #  ),
        line_bot_api.reply_message(
            event.reply_token,  getMythBusters()
        )

    elif event.message.text == 'Emergency & Services':
        msg = 'This is Emergency & Services'
        menu = MainMenu()  # Menu3()
        line_bot_api.reply_message(
            event.reply_token, [
                TextSendMessage(msg),
                menu]
        )
    else:
        msg = "Sorry! I don't understand what you said. Which of the following information you want to know?"
        menu = MainMenu()
        line_bot_api.reply_message(
        event.reply_token, [
            TextSendMessage(msg),
            menu]
        )

# Handler function for Sticker Message
def handle_StickerMessage(event):
    line_bot_api.reply_message(
        event.reply_token,
        StickerSendMessage(
            package_id=event.message.package_id,
            sticker_id=event.message.sticker_id)
    )

# Handler function for Image Message
def handle_ImageMessage(event):
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text="Nice image!")
    )


# Handler function for Video Message
def handle_VideoMessage(event):
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text="Nice video!")
    )


# Handler function for File Message
def handle_FileMessage(event):
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text="Nice file!")
    )


if __name__ == "__main__":
    arg_parser = ArgumentParser(
        usage='Usage: python ' + __file__ + ' [--port <port>] [--help]'
    )
    arg_parser.add_argument('-d', '--debug', default=False, help='debug')
    options = arg_parser.parse_args()

    app.run(host='0.0.0.0', debug=options.debug, port=heroku_port)
