#Imports
import discord
from discord.ext import commands
from discord.ext.commands import has_permissions
from discord_webhook import DiscordWebhook, DiscordEmbed
import pandas as pd
import json
from collections import defaultdict
import os

#Token and Webhook URL
TOKEN = ''
WEBHOOK_URL = ''

#Setting up the bot's configuration
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Bot's status
class Transaction:
    def __init__(self, name, amount):
        self.name = name
        self.amount = amount

#Bot itself
class TransactionProcessor:
    def __init__(self, transactions):
        self.transactions = transactions

#Setting the total amount of fees to 0
        self.gebyr_total = 0

    def sum_amounts_by_name(self):
        amounts_by_name = defaultdict(float)
        for transaction in self.transactions:

#Keep track of the total amount of fees seperately
            if transaction.name == "Gebyr":
                self.gebyr_total += transaction.amount

#Sum the amounts by name
            else:
                amounts_by_name[transaction.name] += transaction.amount
        return [{'Name': name, 'Total Amount': amount} for name, amount in amounts_by_name.items()]

#Invert the amounts since a negative amount means a withdrawal
    def invert_amounts(self, summed_amounts):
        for entry in summed_amounts:
            entry['Total Amount'] = -entry['Total Amount']
        return summed_amounts

#Sort the names by their amounts since we want to see who has the most
    def sort_by_amount(self, summed_amounts):
        return sorted(summed_amounts, key=lambda x: x['Total Amount'], reverse=True)

#Send the leaderboard to Discord via the webhook
    def send_to_discord(self, sorted_amounts):
        webhook = DiscordWebhook(url=WEBHOOK_URL)
        embed = DiscordEmbed(title="Leaderboard", description="-----------------------------------", color=242424)
        for entry in sorted_amounts:
            embed.add_embed_field(name=entry['Name'], value=f"Total Amount: {entry['Total Amount']}", inline=False)
        webhook.add_embed(embed)
        response = webhook.execute()

# Send the total amount for "Gebyr" seperately
        fee_message = f"The total amount that has been paid for fees is:  {self.gebyr_total * -1} kr."
        webhook = DiscordWebhook(url=WEBHOOK_URL, content=fee_message)
        webhook.execute()
        return response

#The command to update the leaderboard and the converter from Excel to JSON:
@bot.command()

#Make sure only administrators can use the command
@has_permissions(administrator=True)
async def update(ctx):

#Check if the user has attached a file
    if not ctx.message.attachments:
        await ctx.send("Please attach a file.")
        return

#Setting up a variable for the file path and the attatched file
    attachment = ctx.message.attachments[0]
    file_path = f"./{attachment.filename}"

#Save the file and return an error message if it fails
    try:
        await attachment.save(file_path)
    except FileNotFoundError:
        await ctx.send("Failed to save the file. Please try again.")
        return

#Convert Excel to JSON
    df = pd.read_excel(file_path)

#Make a list of transactions and process them
    transactions = []
    for _, row in df.iterrows():
        transaction = Transaction(row['Name'], row['Amount'])
        transactions.append(transaction)

#Process the transactions
    processor = TransactionProcessor(transactions)
    summed_amounts = processor.sum_amounts_by_name()
    inverted_amounts = processor.invert_amounts(summed_amounts)
    sorted_amounts = processor.sort_by_amount(inverted_amounts)
    processor.send_to_discord(sorted_amounts)


#Delete the file after it has been processed
    os.remove(file_path)

#Run the bot itself
bot.run(TOKEN)
