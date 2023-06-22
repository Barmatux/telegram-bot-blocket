import asyncio
import os
import pickle
from asyncio import Queue, set_event_loop, new_event_loop
from time import sleep

from selenium.webdriver.chrome.options import Options

import chromedriver_autoinstaller

from requests_html import HTMLSession, AsyncHTMLSession
from selenium import webdriver
from selenium.webdriver.common.by import By
from telegram import Update, Bot
from telegram.ext import CommandHandler, ContextTypes, Updater, CallbackContext

RESULT = []
LAST_ITEM = ''


def find_new_items(last_item: str, new_items: list):
    for i, v in enumerate(new_items):
        if v == last_item:
            return i
    return len(new_items)

def write_file(file_name, values):
    with open(file_name, 'wb') as fi:
        pickle.dump(values, fi)


def stop_check_command(update: Update, context: CallbackContext) -> None:
    """Handler function for the /stop_check command"""

    job = context.chat_data.get('polling_job')

    # Cancel the job if it exists
    if job:
        job.schedule_removal()  # remove the repeating job from the job queue
        del context.chat_data['polling_job']  # remove the job from the context
        update.message.reply_text('Polling job has stopped!')  # send a message to confirm the polling job has stopped
    else:
        update.message.reply_text('There is no active polling job!')

def main():
    """Main function to start the bot and handle commands"""

    # Create the Updater and pass it your bot's token.
    api_key = os.environ['TELEGRAM_TOKEN']
    updater = Updater(api_key)

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher



    # Add command handlers for /start_check and /stop_check
    dispatcher.add_handler(CommandHandler("subscribe", start_check_command))
    dispatcher.add_handler(CommandHandler("unsubscribe", stop_check_command))

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


def start_check_command(update: Update, context: CallbackContext) -> None:
    """Handler function for the /start_check command"""

    # Use the global variables

    polling_interval = 25

    # Get the polling job from the chat_data
    job = context.chat_data.get('polling_job')

    if job:
        # If a polling job is already running, send a message to notify the users
        update.message.reply_text('A polling job is already running!')
    else:
        # Start the repeating job to check the website content every 10 seconds
        job = context.job_queue.run_repeating(send_message_when_website_content_has_changed, interval=polling_interval,
                                              first=0, context=update.message.chat_id)

        # Store the job in the chat_data for later reference
        context.chat_data['polling_job'] = job
        update.message.reply_text('Start monitoring')

def send_message_when_website_content_has_changed(context: CallbackContext):
    # Use the global variable
    global RESULT
    global LAST_ITEM
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    chromedriver_autoinstaller.install()
    driver = webdriver.Chrome(options=options)
    driver.get("https://www.blocket.se/annonser/hela_sverige/fordon/bilar?cg=1020")


    for element in driver.find_elements(By.XPATH, '//div[@data-cy="search-results"]//article'):


        vat_item = element.find_elements(By.XPATH, './/div[contains(@class,"Price__StyledVatPrice")]')
        year = element.find_elements(By.XPATH, './/ul[contains(@class,"ParametersList")]/li')

        if not vat_item or not year or int(year[0].text) < 2018:
            continue

        url = element.find_element(By.XPATH, './/a[contains(@class,"StyledTitleLink")]').get_attribute('href')
        RESULT.append(url)



    new_index = find_new_items(LAST_ITEM, RESULT)
    if new_index:
        for i in RESULT[:new_index]:
            context.bot.send_message(chat_id=context.job.context, text=i)
    LAST_ITEM = RESULT[0]
    RESULT = RESULT[:new_index]



if __name__ == '__main__':
    main()


