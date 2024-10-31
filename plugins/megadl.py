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

from helpers.download_uplaod_helper import send_splitted_file, send_file, humanbytes
from helpers.files_spliiting import split_files, split_video_files
from .mega_logging import m

from functools import partial

if bool(os.environ.get("WEBHOOK", False)):
    from sample_config import Config
else:
    from config import Config

from translation import Translation

import pyrogram
from pyrogram import Client, filters

from pyrogram.errors import UserNotParticipant, UserBannedInChannel
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
logging.getLogger("pyrogram").setLevel(logging.WARNING)

from database.blacklist import check_blacklist
from database.userchats import add_chat

downlaoding_in_megacmd = False

@Client.on_message(filters.regex(pattern=".*http.*"))
async def mega_dl(bot, update):
    global downlaoding_in_megacmd
    fuser = update.from_user.id
    
    if check_blacklist(fuser):
        await update.reply_text("Sorry! You are Banned!")
        return
    
    add_chat(fuser)
    url = update.text
    
    if "mega.nz" in url:
        if ("folder" or "#F" or "#N") not in url:
            usermsg = await bot.send_message(
                chat_id=update.chat.id,
                text=f"""<b>Processing...⏳</b>""",
                reply_to_message_id=update.id
            )
            description = ""
            megalink = None
            
            # Initialize fname at the beginning
            fname = None
            
            error_text = f"""Sorry some error occurred!

Make sure your link is <b>Valid (not expired or been removed)</b>

Make sure your link is <b>not password protected or encrypted or private</b>"""
            
            try:
                linkinfo = m.get_public_url_info(url)
                logger.info(linkinfo)
                if "|" in linkinfo:
                    info_parts = linkinfo.split("|")
                    fsize = info_parts[0]
                    fname = info_parts[1]  # Ensure fname is assigned here
                    logger.info(fsize)
                    logger.info(fname)
                    
            except Exception as e:
                logger.info(e)
                await bot.edit_message_text(
                    chat_id=update.chat.id,
                    text="Error: " + str(e) + "\n\n" + error_text,
                    message_id=usermsg.id
                )
                return
            
            # Check if fname was successfully assigned before using it
            if fname is not None:
                tg_send_type = "vid" if ".mp4" in fname or ".mkv" in fname else "doc"
                
                if ".mp4" in fname:
                    description_parts = fname.split(".mp4")
                    description = description_parts[0]
                    logger.info(description)
                elif ".mkv" in fname:
                    description_parts = fname.split(".mkv")
                    description = description_parts[0]
                    logger.info(description)
                
                try:
                    max_file_size = 2040108421
                    the_file_size = int(fsize)
                    
                    await bot.edit_message_text(
                        chat_id=update.chat.id,
                        text="<b>Files detected</b> : " + fname + "\n" + "<b>Size</b> : " + humanbytes(the_file_size) + "\n" + "\n" + Translation.DOWNLOAD_START,
                        message_id=usermsg.id
                    )
                    
                    megalink = url.strip()
                    
                    s = 1 if update.from_user.id == int(Config.OWNER_ID) or update.from_user.id in Config.AUTH_USERS else 0
                    
                    tmp_directory_for_each_user = (Config.ADMIN_LOCATION if s == 1 else Config.DOWNLOAD_LOCATION) + "/" + str(update.from_user.id) + "/" + str(time.time())
                    
                    if not os.path.isdir(tmp_directory_for_each_user):
                        os.makedirs(tmp_directory_for_each_user)
                        
                    download_directory = tmp_directory_for_each_user + "/" + fname
                    splitted_files_directory = tmp_directory_for_each_user + "/" + str(fsize)
                    thumb_image_path = Config.DOWNLOAD_LOCATION + "/" + str(update.from_user.id) + ".jpg"
                    cred_location = Config.CREDENTIALS_LOCATION + "/mega.ini"
                    
                    start = datetime.now()
                    
                    if downlaoding_in_megacmd:
                        try:
                            loop = get_running_loop()
                            await loop.run_in_executor(None, partial(download_mega_docs, megalink, tmp_directory_for_each_user, cred_location, update))
                        except Exception as e:
                            logger.info(e)
                            await bot.edit_message_text(
                                text="Error: " + str(e),
                                chat_id=update.chat.id,
                                message_id=usermsg.id
                            )
                            shutil.rmtree(tmp_directory_for_each_user)
                            return
                    
                    else:
                        try:
                            downlaoding_in_megacmd = True
                            loop = get_running_loop()
                            await loop.run_in_executor(None, partial(download_mega_files, megalink, tmp_directory_for_each_user))
                            downlaoding_in_megacmd = False
                        except Exception as e:
                            logger.info(e)
                            downlaoding_in_megacmd = False
                            await bot.edit_message_text(
                                text="Error: " + str(e),
                                chat_id=update.chat.id,
                                message_id=usermsg.id
                            )
                            shutil.rmtree(tmp_directory_for_each_user)
                            return
                    
                    file_size = os.stat(download_directory).st_size
                    
                    end_one = datetime.now()
                    time_taken_for_download = (end_one - start).seconds
                    
                    if file_size > 2040108421:
                        try:
                            await bot.edit_message_text(
                                chat_id=update.chat.id,
                                text="<b>Detected Size</b> : " + humanbytes(file_size) + "\n" +
                                     "\n" +
                                     "<i>Splitting files...</i>\n\n<code>The downloaded file is bigger than 2GB! But due to telegram API limits I can't upload files which are bigger than 2GB 🥺. So I will split the files and upload them to you. 😇</code>",
                                message_id=usermsg.id
                            )
                            
                            splitting_size = 2040108421
                            
                            if not os.path.exists(splitted_files_directory):
                                os.makedirs(splitted_files_directory)

                            if tg_send_type == "vid":
                                await split_video_files(download_directory, splitting_size, splitted_files_directory, fname)
                                splitted_in_megadl = 1
                            else:
                                loop = get_running_loop()
                                await loop.run_in_executor(None, partial(split_files, download_directory, splitting_size, splitted_files_directory))
                                splitted_in_megadl = 1

                            if splitted_in_megadl == 1:
                                for root, dirs, files in os.walk(splitted_files_directory):
                                    for filename in files:
                                        logger.info(filename)
                                        splited_file_name = filename
                                        description = splited_file_name
                                        splited_file = splitted_files_directory + "/" + splited_file_name

                                        if filename == "fs_manifest.csv":
                                            continue

                                        await bot.edit_message_text(
                                            chat_id=update.chat.id,
                                            text=Translation.UPLOAD_START,
                                            message_id=usermsg.id
                                        )
                                        await send_splitted_file(bot, update, tg_send_type, thumb_image_path, splited_file, tmp_directory_for_each_user, description, usermsg)

                                end_two = datetime.now()
                                time_taken_for_upload = (end_two - end_one).seconds

                                await bot.edit_message_text(
                                    text=Translation.AFTER_SUCCESSFUL_UPLOAD_MSG_WITH_TS.format(time_taken_for_download, time_taken_for_upload),
                                    chat_id=update.chat.id,
                                    message_id=usermsg.message_id,
                                    disable_web_page_preview=True
                                )

                                try:
                                    shutil.rmtree(tmp_directory_for_each_user)
                                    return
                                except Exception as e:
                                    logger.info(e)
                                    return

                        except Exception as e:
                            await bot.edit_message_text(
                                text="Error: " + str(e),
                                chat_id=update.chat.id,
                                message_id=usermsg.id
                            )
                            try:
                                shutil.rmtree(tmp_directory_for_each_user)
                                return
                            except Exception as e:
                                logger.info(e)
                                return

                    else:
                        try:
                            await bot.edit_message_text(
                                chat_id=update.chat.id,
                                text=Translation.UPLOAD_START,
                                message_id=usermsg.id
                            )
                            
                            await send_file(bot, update, tg_send_type, thumb_image_path, download_directory, tmp_directory_for_each_user, description, usermsg)

                            end_two = datetime.now()
                            time_taken_for_upload = (end_two - end_one).seconds

                            await bot.edit_message_text(
                                text=Translation.AFTER_SUCCESSFUL_UPLOAD_MSG_WITH_TS.format(time_taken_for_download, time_taken_for_upload),
                                chat_id=update.chat.id,
                                message_id=usermsg.id,
                                disable_web_page_preview=True
                            )

                            try:
                                shutil.rmtree(tmp_directory_for_each_user)
                                return
                            except Exception as e:
                                logger.info(e)
                                return

                        except Exception as e:
                            logger.info(e)
                            
                            await bot.edit_message_text(
                                text="Error: " + str(e),
                                chat_id=update.chat.id,
                                message_id=usermsg.id
                            )
                            
                            try:
                                shutil.rmtree(tmp_directory_for_each_user)
                                return
                            except Exception as e:
                                logger.info(e)
                                return
                
            else:  # If fname was not assigned successfully.
                await bot.edit_message_text(
                    chat_id=update.chat.id,
                    text="Error: File name could not be determined.",
                    message_id=usermsg.id
                )
                
        else:  # Handle folder links.
            await bot.send_message(
                chat_id=update.chat.id,
                text=f"""Sorry! Folder links are not supported!""",
                reply_to_message_id=update.id
            )
            return
            
    else:  # Handle invalid links.
        await bot.send_message(
            chat_id=update.chat.id,
            text=f"""<b>I am a mega.nz link downloader bot! 😑</b>\n\nThis is not a mega.nz link. 😡""",
            reply_to_message_id=update.id
        )
        return


def download_mega_files(megalink, tmp_directory_for_each_user):
    try:
        global downlaoding_in_megacmd
        
        process = subprocess.run(["mega-get", megalink, tmp_directory_for_each_user]) 
    except Exception as e:
        downlaoding_in_megacmd = False
        logger.info(e)


def download_mega_docs(megalink, tmp_directory_for_each_user, cred_location, update):
    try:
        if os.path.exists(cred_location):
            try:
                process = subprocess.run(["megadl", megalink, "--path", tmp_directory_for_each_user, "--config", cred_location])
            except Exception as e:
                logger.info(e)
                update.reply_text(f"Error : `{e}` occurred!\n\n<b>.Maybe because there is some error in your `mega.ini` file! Please send your file exactly as mentioned in the readme 👉 https://github.com/XMYSTERlOUSX/mega-link-downloader-bot/blob/main/README.md</b>\n\n<i>Downloading your file now without logging in to your account...</i>", disable_web_page_preview=True)
                process = subprocess.run(["megadl", megalink, "--path", tmp_directory_for_each_user])
        else:
            process = subprocess.run(["megadl", megalink, "--path", tmp_directory_for_each_user])
    except Exception as e:
        logger.info(e)
                
