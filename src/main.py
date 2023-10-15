import discord
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import pandas as pd
import gzip
from urllib.request import urlopen, Request
import datetime
from src.constants import (
    BOT_INVITE_URL,
    DISCORD_BOT_TOKEN,
)
import logging
logger = logging.getLogger(__name__)
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

client = discord.Client(intents=intents)
tree = discord.app_commands.CommandTree(client)
user_submissions = {}

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.141 Safari/537.36",
        "Accept": 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": "https://www.google.com/",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
}

def is_valid_url(url):
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False
    
def contains_required_tags(soup, required_tags):
    # Find all 'a' tags with class 'link'
    hashtag_elements = soup.find_all('a', class_='link')
    
    # Extract hashtags from the elements
    hashtags = [element.text for element in hashtag_elements if element.text.startswith('#')]
    
    # Check if all required tags are in the extracted hashtags
    return all(tag in hashtags for tag in required_tags)

def parse_link_data(link,required_tags):
    req_product = Request(link, headers=headers)
    response_product = urlopen(req_product)
    charset_product = response_product.headers.get_content_charset()
    if response_product.headers.get('Content-Encoding') == 'gzip':
        content_product = gzip.decompress(response_product.read()).decode(charset_product)
    else:
        content_product = response_product.read().decode(charset_product)
    soup_product = BeautifulSoup(content_product, 'html.parser')

    return contains_required_tags(soup_product, required_tags)

    


@client.event
async def on_ready():
    logger.info(f"We have logged in as {client.user}. Invite URL: {BOT_INVITE_URL}")
    daily_verification.start()

# ... [rest of your code]
join_challenge_enabled = True
CORRECT_EVENT_NAME = "code_365"
EVENT_ORGANIZER_ROLE = "mod"

@tree.command(name="toggle_join", description="Enable/Disable join challenge command")
async def toggle_join_challenge(int: discord.Interaction):
    global join_challenge_enabled

    # Check if the user has the EVENT_ORGANIZER_ROLE
    member = int.guild.get_member(int.user.id)
    if EVENT_ORGANIZER_ROLE not in [role.name for role in member.roles]:
        await int.response.send_message("You do not have the permissions to use this command.", ephemeral=True)
        return

    # Toggle the command status
    join_challenge_enabled = not join_challenge_enabled

    await int.response.send_message(f"Join challenge command has been {'enabled' if join_challenge_enabled else 'disabled'}.", ephemeral=True)

@tree.command(name="join_challange", description="Join the event")
async def joinchallenge_command(int: discord.Interaction,  event_name: str):
    
    global join_challenge_enabled

    if not join_challenge_enabled:
        await int.response.send_message("Joining the challenge is currently disabled.", ephemeral=True)
        return

    if event_name != CORRECT_EVENT_NAME:
        await int.response.send_message("Invalid event name provided.", ephemeral=True)
        return
    
    user_id = int.user.id
    user_name = int.user.name
    
    # If the user is already part of the challenge
    if user_id in user_submissions:
        await int.response.send_message(f"{user_name}, you are already part of the challenge!", ephemeral=True)
        return

    # Add the user to the challenge
    user_submissions[user_id] = {
    'username': user_name,
    'eligible': True,
    'current_day': True,
    'days': 0 
    }
    # initialize the days value to 0 when a user joins


    
    await int.response.send_message(f"{user_name}, you have successfully joined the challenge!", ephemeral=True)

# ... [rest of your code]

@tree.command(name="submit", description="Submit a link for daily progress")
async def submit_command(int: discord.Interaction, link: str):
    user_id = int.user.id
    if user_id not in user_submissions:
        await int.response.send_message(f"Sorry {int.user.name}, you are not registered for this event", ephemeral=True)
    eligibility = user_submissions.get(user_id, {}).get('eligible', True)
    if not eligibility:
        await int.response.send_message(f"Sorry {int.user.name}, you are not eligible to submit. You have been disqualified.", ephemeral=True)
        return
    required_tags = ["#internship2023"]
    day = datetime.datetime.now().strftime("%Y-%m-%d")
    if day not in user_submissions[user_id]:
        user_submissions[user_id]['days'] += 1
    if user_id not in user_submissions:
        user_submissions[user_id] = {'username': int.user.name}
    user_submissions[user_id][day] = link
    
    if not is_valid_url(link):
        await int.response.send_message("The provided link is not valid. Please provide a valid LinkedIn or Twitter URL.", ephemeral=True)
        return
    parsed_data = parse_link_data(link, required_tags)
    if parsed_data:
        user_submissions[user_id]['current_day'] = True
        await int.response.send_message(f"Submission for {day} validated successfully.", ephemeral=True)
        return
    else:
        user_submissions[user_id]['current_day'] = False
        await int.response.send_message(f"Your submission for {day} is missing the required tags. Please submit a valid post.", ephemeral=True)
        return

@tree.command(name="leaderboard", description="Display the leaderboard with eligibility status")
async def leaderboard_command(int: discord.Interaction):
    # Check if the user has the required role to use this command
    member = int.guild.get_member(int.user.id)
    if EVENT_ORGANIZER_ROLE not in [role.name for role in member.roles]:
        await int.response.send_message("You do not have the permissions to use this command.", ephemeral=True)
        return

    # Construct the leaderboard message
    leaderboard_entries = []
    for user_id, data in user_submissions.items():
        username = data.get('username')
        eligibility_status = "Eligible" if data.get('eligible', True) else "Ineligible"
        consecutive_days = data.get('days', 0)
        leaderboard_entries.append(f"{username} - {eligibility_status} - Day {consecutive_days}")
    
    leaderboard_message = "\n".join(leaderboard_entries)

    # If there's no data
    if not leaderboard_message:
        await int.response.send_message("No participants yet.", ephemeral=True)
        return

    await int.response.send_message(f"**Leaderboard:**\n{leaderboard_message}", ephemeral=True)

@tree.command(name="check_eligibility", description="Check eligibility of a user")
async def check_eligibility_command(int: discord.Interaction, user: discord.User = None):
    user_id = user.id if user else int.user.id
    eligibility = user_submissions.get(user_id, {}).get('eligible', True)
    await int.response.send_message(f"{user.name if user else int.user.name} is {'eligible' if eligibility else 'ineligible'} for rewards.")

from discord.ext import tasks

@tasks.loop(hours=24)
async def daily_verification():
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    for user_id, submissions in user_submissions.items():
        if today not in submissions or not submissions.get('current_day', False):
            # Mark user as ineligible
            user_submissions[user_id]['eligible'] = False
            # Notify user
            user = client.get_user(user_id)
            await user.send("You missed a submission for today or your submission was invalid. You are marked as ineligible for rewards.")



# This will store user_id: { day: post_link, ... }


client.run(DISCORD_BOT_TOKEN)



#to run python -m src.main