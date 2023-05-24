import asyncio
from math import ceil, floor
from threading import Lock
from typing import Optional
import itertools

import discord
from discord.ext import commands

from db import DB

intents = discord.Intents.default()
bot = discord.Bot(intents = intents)

forumPostDescription = "Discuss how this normal card would be placed into the tier list! Assuming how easily it can be used in general or placed into a deck. Factors which contribute to this include offense, (poking/piercing, flanking, winning clashes, good special tile placement so you can easily special attack from it later) defense, (blocking, establishing routes, map control/occupying space, good normal/special tile placement so it isn't easily special attacked over later) openings, (meaning its played on the 1st turn) special building, (combo ability, how easy is it to activate the card's special point) special attacks, (this can be considered for all aspects of the match which is early/mid/endgame) its ability to be played at any time, (wont be a brick/unusable past a specific point) and finally the niche situations that it would be usable in if thats applicable. Which is described in the voting channel. (Note that every map is considered in discussions except for Box Seats)"
forumPostMapDescription = "Discuss how this map would be placed into the tier list! Assuming this map is played in a competitive Tableturf Battle tournament. Factors which contribute to this include the design of the map, (how easy is it to access certain parts of the map, what does the design of the map encourage/discourage) level of card/deck dependency, allowance of several strategies/playstyles, overcentralizing strategies/playstyles, map size, (both in the literal size of the stage and areas concerning parts of the map) and starting special tile location. (how far away is it from the opposing starting special tile location)"

highest_possible_vote = 10

def reactions(n):
    if n > highest_possible_vote:
        raise ValueError("Only <{highest_possible_vote} are supported")

    nums = range(1, n)
    extra = []
    if n == 10:
        extra = [0]
    else:
        extra = [n]
    return [str(x)+"\N{combining enclosing keycap}" for x in itertools.chain(nums, extra)]

def score_from_reaction_name(name: str) -> Optional[int]:
    if name not in reactions(highest_possible_vote):
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
        "channel",
        discord.ForumChannel,
    )
    @commands.has_any_role("Whopper")
    async def set_forum_channel(self, ctx: discord.ApplicationContext, channel: discord.ForumChannel):
        self.mutex.acquire()
        self.db.set_forum_chan(channel.id)
        await ctx.respond(f"Ok! I will create forum posts in <#{channel.id}> from now on.")
        self.mutex.release()

    @commands.slash_command()
    @discord.option(
        "size",
        description = "How many cards to vote on in this group, at most.",
        min_value = 1,
        max_value = 6,
        default = 4,
    )
    @discord.option(
        "type",
        description = "Thing to vote on.",
        choices = ["card", "map"],
        default = "card",
    )
    @commands.has_any_role("Whopper")
    async def start(self, ctx: discord.ApplicationContext, size: int, type: str):
        self.mutex.acquire()

        forum_ch_id = self.db.get_forum_chan()
        if forum_ch_id is None:
            await ctx.respond("Please set a forum channel with /set_forum_channel first.")
            self.mutex.release()
            return

        forum_ch = self.bot.get_channel(forum_ch_id)
        if forum_ch is None:
            await ctx.respond("Could not find forum channel - try resetting it?")
            self.mutex.release()
            return

        if self.in_progress:
            await ctx.respond("A round already in progress.")
            self.mutex.release()
            return
        
        # If there are messages in the channel, we are in progress
        if self.db.get_messages(ctx.channel_id):
            await ctx.respond("A round already in progress.")
            self.in_progress = True
            self.mutex.release()
            return
        
        self.in_progress = True

        if type == "card":
            await ctx.respond(f"Ok! Starting a new round with at most {size} {self.db.get_lowest_cost()}-cost cards.")
        else:
            await ctx.respond(f"Ok! Starting a new round with at most {size} maps.")

        # Delete summaries from the previous round
        ch = self.bot.get_channel(ctx.channel_id)
        for item in self.db.get_summaries(ctx.channel_id):
            msg = await ch.fetch_message(item[0])
            if msg is None:
                self.db.remove_summary(item[0])
                continue
            if self.should_delete_messages:
                await msg.delete()
            self.db.remove_summary(item[0])

        things = []
        if type == "card":
            things = self.db.get_card_group(size)
        else:
            things = self.db.get_map_group(size)

        if not things:
            await ctx.send("There's nothing left to do!")

        msgs = []
        forum_posts = []
        for thing in things:
            txt = ""
            if type == "card":
                txt = f"No. {thing[0]} {thing[1]} ({thing[2]})"
            else:
                txt = thing[1]


            # Send message and set reactions on it
            msg = await ctx.send(
                txt,
                file = discord.File(
                    self.db.get_img(thing[0], type == "map"),
                    filename=thing[1].lower().replace(" ", "_") + ".jpg",
                ),
            )

            max_vote = 10
            if type == "map":
                max_vote = 5

            pending = []
            for r in reactions(max_vote):
                pending.append(msg.add_reaction(discord.PartialEmoji(name=r)))
            group = asyncio.gather(*pending, return_exceptions=True)
            await group

            msgs.append((ctx.channel_id, msg.id, thing[0]))

            # Find the relevant tag
            tags = []
            for tag in forum_ch.available_tags:
                if type == "card":
                    if tag.name == f"{self.db.get_lowest_cost()}-Cost":
                        tags.append(tag)
                        break
                else:
                    if tag.name == "Map":
                        tags.append(tag)
                        break

            # Create the forum post
            #
            # This is a hack. Pycord does not support creating a thread with files directly.
            # Instead the thread must be created, then edited to add the file.
            #
            # See
            # https://github.com/Pycord-Development/pycord/issues/1948
            # https://github.com/Pycord-Development/pycord/issues/1949
            desc = forumPostDescription
            if type == "map":
                desc = forumPostMapDescription
            thread = await forum_ch.create_thread(
                name = thing[1],
                content = desc,
                applied_tags = tags,
            )

            forum_posts.append((thread.id,))

            message = await thread.fetch_message(thread.id)
            await message.edit(file=discord.File(
                    self.db.get_img(thing[0], type == "map"),
                    filename=thing[1].lower().replace(" ", "_") + ".jpg",
                ))
        
        self.db.insert_messages(msgs)
        self.db.insert_forum_posts(forum_posts)
        self.db.set_round_type(type)
        self.mutex.release()

    @commands.slash_command()
    @commands.has_any_role("Whopper")
    async def stop(self, ctx: discord.ApplicationContext):
        self.mutex.acquire()
        # If there are messages, we are in progress
        if self.db.get_messages(ctx.channel_id):
            self.in_progress = True

        if not self.in_progress:
            await ctx.respond("A round is not in progress.")
            self.mutex.release()
            return

        await ctx.respond("Ok! Tallying votes :)")

        # Lock threads from the previous round
        for item in self.db.get_forum_posts():
            thread = await self.bot.fetch_channel(item[0])
            if thread is None:
                self.db.remove_forum_post(item[0])
                continue
            await thread.edit(locked=True)

        ch = self.bot.get_channel(ctx.channel_id)
        msgs = self.db.get_messages(ctx.channel_id)

        type = self.db.get_round_type()
        summaries = []
        for item in msgs:
            msg = await ch.fetch_message(item[0])
            if msg is None:
                self.db.remove_message(item[0])
            
            max_vote = 10
            if type == "map":
                max_vote = 5

            scores = [0]*max_vote
            for r in msg.reactions:
                score = score_from_reaction_name(r.emoji)
                if score is None:
                    continue
                # Be sure to remove our own reaction
                scores[score-1] = r.count - 1
            
            # Insert the votes for the thing
            # and mark it as having been voted on so it isn't picked again
            txt = ""
            if type == "card":
                self.db.add_scores(item[1], scores)
                self.db.mark_has_voted(item[1])
                txt = f"No. {item[1]} {self.db.get_name(item[1])}"
            else:
                self.db.add_map_scores(item[1], scores)
                self.db.mark_map_has_voted(item[1])
                txt = self.db.get_map_name(item[1])

            removed, total, avg = weighted_average(scores.copy())

            # Send a message with information about the scores
            summary = await ctx.send(
                "\n".join([
                    txt,
                    "Raw votes: " + ",".join([str(x) for x in scores]),
                    "Total after removal: " + str(total),
                    f"Score: {avg:.4f}",
                ])
            )

            summaries.append((ctx.channel_id, summary.id))

            # Clean up our message
            if self.should_delete_messages:
                await msg.delete()

            # Remove that message from the table
            self.db.remove_message(item[0])

        if type == "card":
            cost = self.db.get_lowest_cost()
            left = self.db.number_for_cost(cost)
            summary = await ctx.send(f"There are {left} cards with cost {cost} remaining.")
            summaries.append((ctx.channel_id, summary.id))
        else:
            summary = await ctx.send(f"There are {self.db.maps_left()} maps remaining.")
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
        return (0, 0, 0)
    
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