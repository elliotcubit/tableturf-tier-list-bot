import asyncio
from math import ceil, floor
from threading import Lock
from typing import Optional

import discord
from discord.ext import commands

from db import DB

intents = discord.Intents.default()
bot = discord.Bot(intents = intents)

reactions = [str(x)+"\N{combining enclosing keycap}" for x in list(range(1,10))+[0]]
def score_from_reaction_name(name: str) -> Optional[int]:
    if name not in reactions:
        return None
    s = int(name[0])
    # Zero means ten, since there's no ten keycap (?)
    if s == 0:
        s = 10
    return s

class Poller(commands.Cog):
    def __init__(self, bot: discord.Bot, db: DB, should_delete_messages: bool):
        self.bot = bot
        self.db = db
        self.should_delete_messages = should_delete_messages
        self.mutex = Lock()
        self.in_progress = False

    @commands.slash_command()
    @discord.option(
        "size",
        description = "How many cards to vote on in this group, at most",
        min_value = 1,
        max_value = 6,
        default = 4,
    )
    @commands.has_any_role("Whopper")
    async def start(self, ctx: discord.ApplicationContext, size: int):
        self.mutex.acquire()
        if self.in_progress:
            await ctx.respond("round already in progress")
            self.mutex.release()
            return
        
        # If there are messages in the channel, we are in progress
        if self.db.get_messages(ctx.channel_id):
            await ctx.respond("round already in progress")
            self.in_progress = True
            self.mutex.release()
            return
        
        self.in_progress = True
        await ctx.respond("ok!")

        # Delete summaries from the previous round
        ch = self.bot.get_channel(ctx.channel_id)
        for item in self.db.get_summaries(ctx.channel_id):
            msg = await ch.fetch_message(item[0])
            if msg is None:
                self.db.remove_summary(item[0])
            if self.should_delete_messages:
                await msg.delete()
            self.db.remove_summary(item[0])

        msgs = []

        for card in self.db.get_next_group(size):
            img = self.db.get_img(card[0])

            msg = await ctx.send(
                f"No. {card[0]} {card[1]} ({card[2]})",
                file = discord.File(
                    img,
                    filename=card[1].lower().replace(" ", "_") + ".jpg",
                ),
            )

            pending = []
            for r in reactions:
                pending.append(msg.add_reaction(discord.PartialEmoji(name=r)))
            group = asyncio.gather(*pending, return_exceptions=True)
            await group

            msgs.append((ctx.channel_id, msg.id, card[0]))
        
        self.db.insert_messages(msgs)
        self.mutex.release()

    @commands.slash_command()
    @commands.has_any_role("Whopper")
    async def stop(self, ctx: discord.ApplicationContext):
        self.mutex.acquire()
        # If there are messages, we are in progress
        if self.db.get_messages(ctx.channel_id):
            self.in_progress = True

        if not self.in_progress:
            await ctx.respond("round is not in progress")
            self.mutex.release()
            return

        await ctx.respond("ok!")

        ch = self.bot.get_channel(ctx.channel_id)
        msgs = self.db.get_messages(ctx.channel_id)
        cost = self.db.get_lowest_cost()

        summaries = []

        for item in msgs:
            msg = await ch.fetch_message(item[0])
            if msg is None:
                self.db.remove_message(item[0])
            
            scores = [0]*10
            for r in msg.reactions:
                score = score_from_reaction_name(r.emoji)
                if score is None:
                    continue
                # Be sure to remove our own reaction
                scores[score-1] = r.count - 1
            
            # Insert the votes for the card
            self.db.add_scores(item[1], scores)

            # Mark it as having been voted on so it isn't picked again
            self.db.mark_has_voted(item[1])

            # Send a message with information about the scores
            name = self.db.get_name(item[1])
            removed, total, avg = weighted_average(scores.copy())

            summary = await ctx.send(
                "\n".join([
                    f"No. {item[1]} {name}:",
                    "Raw votes: " + ",".join([str(x) for x in scores]),
                    "Total after removal: " + str(total),
                    "Score: " + str(avg),
                ])
            )

            summaries.append((ctx.channel_id, summary.id))

            # Clean up our message
            if self.should_delete_messages:
                await msg.delete()

            # Remove that message from the table
            self.db.remove_message(item[0])

        

        left = self.db.number_for_cost(cost)
        summary = await ctx.send(f"There are {left} cards with cost {cost} remaining.")
        summaries.append((ctx.channel_id, summary.id))

        self.db.insert_summaries(summaries)

        self.in_progress = False
        self.mutex.release()

# We want to round half upwards, so here is a helper
def normal_round(n):
    if n - floor(n) < 0.5:
        return floor(n)
    return ceil(n)

# Computes the weighted average of the list after removing
# the top and bottom 10% of votes.
def weighted_average(lst):
    total_votes = sum(lst)
    if total_votes == 0:
        return (0, 0)
    
    to_remove = normal_round((total_votes/10)+0.01)

    def remove(idxs):
        removed = 0
        for i in idxs:
            if lst[i] > 0:
                # If we can remove all needed votes from this slot do so
                if lst[i] > (to_remove - removed):
                    lst[i] -= (to_remove - removed)
                    removed = to_remove
                    break
                # otherwise, remove what we can
                else:
                    removed += lst[i]
                    lst[i] = 0

    remove(range(len(lst)))
    remove(range(len(lst))[::-1])
    
    s = 0
    for i in range(len(lst)):
        s += (i+1)*lst[i]
    
    return (to_remove, s, s/(total_votes - (to_remove * 2)))

def setup(bot: discord.Bot, db: DB, should_delete_messages: bool = False):
    bot.add_cog(Poller(bot, db, should_delete_messages))