import logging
import asyncio
import json
import math
import subprocess
import os
import shutil
import time
from datetime import datetime
from asyncio import get_running_loop
from functools import partial

from helpers.download_uplaod_helper import send_splitted_file, send_file, humanbytes
from helpers.files_spliiting import split_files, split_video_files
from .mega_logging import m

from config import Config if not os.environ.get("WEBHOOK", False) else sample_config
from translation import Translation

import pyrogram
from pyrogram import Client, filters
from pyrogram.errors import UserNotParticipant, UserBannedInChannel
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from database.blacklist import check_blacklist
from database.userchats import add_chat

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logging.getLogger("pyrogram").setLevel(logging.WARNING)

downloading_in_megacmd = False

@Client.on_message(filters.regex(pattern=".*http.*"))
async def mega_dl(bot, update):
    global downloading_in_megacmd
    user_id = update.from_user.id

    if check_blacklist(user_id):
        await update.reply_text("Sorry! You are Banned!")
        return
    
    add_chat(user_id)
    url = update.text.strip()

    if "mega.nz" not in url:
        await bot.send_message(
            chat_id=update.chat.id,
            text="<b>I am a mega.nz link downloader bot! 😑</b>\n\nThis not a mega.nz link. 😡",
            reply_to_message_id=update.id
        )
        return

    if "folder" in url or "#F" in url or "#N" in url:
        await bot.send_message(
            chat_id=update.chat.id,
            text="Sorry! Folder links are not supported!",
            reply_to_message_id=update.id
        )
        return

    usermsg = await bot.send_message(
        chat_id=update.chat.id,
        text="<b>Processing...⏳</b>",
        reply_to_message_id=update.id
    )

    error_text = """Sorry, an error occurred!
Make sure your link is <b>Valid (not expired or removed)</b>
Make sure your link is <b>not password protected or encrypted or private</b>"""

    try:
        linkinfo = m.get_public_url_info(url)
        logger.info(linkinfo)
        fsize, fname = linkinfo.split("|") if "|" in linkinfo else (None, None)

        if fsize is None or fname is None:
            raise ValueError("Invalid link information.")

        tg_send_type = "vid" if any(ext in fname for ext in [".mp4", ".mkv"]) else "doc"
        description = fname.rsplit('.', 1)[0]  # Split at the last dot to get the name

    except Exception as e:
        logger.info(e)
        await bot.edit_message_text(chat_id=update.chat.id, text=f"Error: {e}\n\n{error_text}", message_id=usermsg.id)
        return

    await bot.edit_message_text(
        chat_id=update.chat.id,
        text=f"<b>Files detected</b>: {fname}\n<b>Size</b>: {humanbytes(int(fsize))}\n\n{Translation.DOWNLOAD_START}",
        message_id=usermsg.id
    )

    admin_location = Config.ADMIN_LOCATION if user_id == int(Config.OWNER_ID) or user_id in Config.AUTH_USERS else Config.DOWNLOAD_LOCATION
    tmp_directory_for_each_user = os.path.join(admin_location, str(user_id), str(time.time()))
    os.makedirs(tmp_directory_for_each_user, exist_ok=True)

    download_directory = os.path.join(tmp_directory_for_each_user, fname)
    cred_location = os.path.join(Config.CREDENTIALS_LOCATION, "mega.ini")

    start = datetime.now()
    try:
        if downloading_in_megacmd:
            await get_running_loop().run_in_executor(None, partial(download_mega_docs, url, tmp_directory_for_each_user, cred_location, update))
        else:
            downloading_in_megacmd = True
            await get_running_loop().run_in_executor(None, partial(download_mega_files, url, tmp_directory_for_each_user))
            downloading_in_megacmd = False
    except Exception as e:
        logger.info(e)
        await bot.edit_message_text(text=f"Error: {e}", chat_id=update.chat.id, message_id=usermsg.id)
        shutil.rmtree(tmp_directory_for_each_user, ignore_errors=True)
        return

    try:
        file_size = os.stat(download_directory).st_size
        end_one = datetime.now()
        time_taken_for_download = (end_one - start).seconds

        if file_size > 2040108421:  # If file is larger than 2GB
            await bot.edit_message_text(
                chat_id=update.chat.id,
                text=f"<b>Detected Size</b>: {humanbytes(file_size)}\n\n<i>Splitting files...</i>\n\n<code>The downloaded file is bigger than 2GB! Splitting...</code>",
                message_id=usermsg.id
            )
            splitting_size = 2040108421
            splitted_files_directory = os.path.join(tmp_directory_for_each_user, str(file_size))
            os.makedirs(splitted_files_directory, exist_ok=True)

            await (split_video_files(download_directory, splitting_size, splitted_files_directory, fname) if tg_send_type == "vid"
                   else get_running_loop().run_in_executor(None, partial(split_files, download_directory, splitting_size, splitted_files_directory)))

            for filename in os.listdir(splitted_files_directory):
                if filename == "fs_manifest.csv":
                    continue
                splited_file = os.path.join(splitted_files_directory, filename)
                await bot.edit_message_text(chat_id=update.chat.id, text=Translation.UPLOAD_START, message_id=usermsg.id)
                await send_splitted_file(bot, update, tg_send_type, Config.THUMB_IMAGE_PATH, splited_file, tmp_directory_for_each_user, filename, usermsg)

            await bot.edit_message_text(
                text=Translation.AFTER_SUCCESSFUL_UPLOAD_MSG_WITH_TS.format(time_taken_for_download, time_taken_for_upload),
                chat_id=update.chat.id,
                message_id=usermsg.message_id,
                disable_web_page_preview=True
            )
        else:
            await bot.edit_message_text(chat_id=update.chat.id, text=Translation.UPLOAD_START, message_id=usermsg.id)
            await send_file(bot, update, tg_send_type, Config.THUMB_IMAGE_PATH, download_directory, tmp_directory_for_each_user, description, usermsg)
            end_two = datetime.now()
            time_taken_for_upload = (end_two - end_one).seconds
            await bot.edit_message_text(
                text=Translation.AFTER_SUCCESSFUL_UPLOAD_MSG_WITH_TS.format(time_taken_for_download, time_taken_for_upload),
                chat_id=update.chat.id,
                message_id=usermsg.id,
                disable_web_page_preview=True
            )

        shutil.rmtree(tmp_directory_for_each_user, ignore_errors=True)
    except Exception as e:
        logger.info(e)
        await bot.edit_message_text(text=f"Error: {e}", chat_id=update.chat.id, message_id=usermsg.id)
        shutil.rmtree(tmp_directory_for_each_user, ignore_errors=True)

def download_mega_files(megalink, tmp_directory_for_each_user):
    try:
        process = subprocess.run(["mega-get", megalink, tmp_directory_for_each_user])  # Download using MEGAcmd
    except Exception as e:
        logger.info(e)

def download_mega_docs(megalink, tmp_directory_for_each_user, cred_location, update):
    try:
        command = ["megadl", megalink, "--path", tmp_directory_for_each_user]
        if os.path.exists(cred_location):
            command += ["--config", cred_location]
        
        process = subprocess.run(command)  # Download using megadl
    except Exception as e:
        logger.info(e)
        update.reply_text(f"Error: `{e}` occurred!\n\n<b>There may be an issue with your `mega.ini` file!</b>", disable_web_page_preview=True)
