import discord
from discord.ext import commands
import os
import json
import asyncio
from dotenv import load_dotenv
from keep_alive import keep_alive

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

TOKEN = os.getenv('DISCORD_TOKEN')

# --- DIAGNOSTIC STARTUP CHECK ---
if TOKEN:
    print(f"Startup Check: Token found in environment (length: {len(TOKEN)})")
    print(f"Startup Check: Token starts with: {TOKEN[:5]}...")
else:
    print("Startup Check: CRITICAL WARNING - No DISCORD_TOKEN found in environment variables!")
    print("Startup Check: Ensure you have set DISCORD_TOKEN in your Render/Heroku Dashboard.")
# --------------------------------

# Configuration for intents
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

CONFIG_FILE = 'role_tags.json'

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {}
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

def get_guild_config(guild_id):
    """
    Helper to safely get a guild's config.
    Returns a dict with 'default_tag' and 'roles' keys.
    """
    config = load_config()
    guild_id_str = str(guild_id)
    
    if guild_id_str not in config:
        config[guild_id_str] = {"default_tag": None, "roles": {}}
        # If the file was in the old format (flat), we might want to migrate or ignore.
        # For now, we assume fresh start or manual migration if needed, 
        # as detecting "old format" vs "new format" is tricky without specific keys.
        # But we can check if keys look like role IDs (integers) at the top level.
    
    return config.get(guild_id_str, {"default_tag": None, "roles": {}})

def update_guild_config(guild_id, key, value):
    """
    Updates a specific key in the guild's config.
    key can be 'default_tag' or a role_id (which goes into 'roles').
    """
    config = load_config()
    guild_id_str = str(guild_id)
    
    if guild_id_str not in config:
        config[guild_id_str] = {"default_tag": None, "roles": {}}
        
    if key == 'default_tag':
        config[guild_id_str]['default_tag'] = value
    else:
        # Assume key is role_id
        if "roles" not in config[guild_id_str]:
             config[guild_id_str]["roles"] = {}
        config[guild_id_str]["roles"][key] = value
        
    save_config(config)

def remove_guild_role_config(guild_id, role_id):
    config = load_config()
    guild_id_str = str(guild_id)
    
    if guild_id_str in config and "roles" in config[guild_id_str]:
        if role_id in config[guild_id_str]["roles"]:
            del config[guild_id_str]["roles"][role_id]
            save_config(config)
            return True
    return False

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    print(f'Bot ID: {bot.user.id}')
    print(f'Connected to {len(bot.guilds)} guilds')
    print('--- Ready ---')

@bot.command(name='settings')
@commands.has_permissions(manage_nicknames=True)
async def show_settings(ctx):
    """
    Shows the current configuration for this server.
    Usage: !settings
    """
    guild_config = get_guild_config(ctx.guild.id)
    
    embed = discord.Embed(title=f"Settings for {ctx.guild.name}", color=discord.Color.blue())
    
    default_tag = guild_config.get('default_tag')
    embed.add_field(name="Default Tag", value=default_tag if default_tag else "None", inline=False)
    
    roles_msg = ""
    roles_config = guild_config.get("roles", {})
    if roles_config:
        for role_id, tag in roles_config.items():
            role = ctx.guild.get_role(int(role_id))
            role_name = role.name if role else f"Unknown Role ({role_id})"
            roles_msg += f"**{role_name}**: {tag}\n"
    else:
        roles_msg = "No roles configured."
        
    embed.add_field(name="Role Tags", value=roles_msg, inline=False)
    
    await ctx.send(embed=embed)

@bot.command(name='presentrole')
async def present_role(ctx):
    """
    Placeholder for presentrole command.
    """
    await ctx.send("This command is currently not implemented.")

@bot.command(name='pingnick')
async def ping(ctx):
    """
    Checks if the bot is responsive.
    Usage: !pingnick
    """
    await ctx.send(f'Pong! 🏓 Latency: {round(bot.latency * 1000)}ms')

@bot.command(name='autonick')
@commands.has_permissions(manage_nicknames=True)
async def set_auto_nick(ctx, role: discord.Role, tag: str):
    """
    Sets a tag for a specific role.
    Usage: !autonick @Role [Tag]
    Example: !autonick @Moderator [Mod]
    """
    update_guild_config(ctx.guild.id, str(role.id), tag)
    await ctx.send(f'Updated: Users with role **{role.name}** will get the tag **{tag}**.')

@bot.command(name='defaultnick')
@commands.has_permissions(manage_nicknames=True)
async def set_default_nick(ctx, tag: str):
    """
    Sets the default tag for users who do NOT have any configured roles.
    Usage: !defaultnick [Tag]
    Example: !defaultnick [Member]
    """
    update_guild_config(ctx.guild.id, 'default_tag', tag)
    await ctx.send(f'Updated: Users without special roles will get the default tag **{tag}**.')

@bot.command(name='removenick')
@commands.has_permissions(manage_nicknames=True)
async def remove_auto_nick(ctx, role: discord.Role):
    """
    Removes the tag configuration for a specific role AND removes the tag from all users.
    Usage: !removenick @Role
    """
    role_id = str(role.id)
    guild_config = get_guild_config(ctx.guild.id)
    
    if role_id not in guild_config.get("roles", {}):
        await ctx.send(f'No configuration found for role **{role.name}**.')
        return

    tag_to_remove = guild_config["roles"][role_id]
    
    # 1. Delete from config
    remove_guild_role_config(ctx.guild.id, role_id)
    
    await ctx.send(f"Removed config for **{role.name}**. Now removing tag '**{tag_to_remove}**' from existing users...")

    # 2. Remove tag from users
    count = 0
    errors = 0
    
    for member in role.members:
        if not member.nick or tag_to_remove not in member.nick:
            continue
            
        # Permission checks
        if member.id == ctx.guild.owner_id: continue
        if member.top_role >= ctx.guild.me.top_role: continue

        # Remove the tag
        new_nick = member.nick.replace(f" {tag_to_remove}", "")
        if new_nick == member.nick:
            new_nick = member.nick.replace(tag_to_remove, "")
            
        new_nick = new_nick.strip()
        
        try:
            await member.edit(nick=new_nick if new_nick else None)
            count += 1
        except Exception as e:
            print(f"Failed to strip {member.name}: {e}")
            errors += 1
            
    await ctx.send(f"**Complete**: Config deleted and tag removed from {count} users.")

@bot.command(name='updateall')
@commands.has_permissions(manage_nicknames=True)
async def update_all_users(ctx, role: discord.Role = None):
    """
    Updates the nickname for ALL users.
    If a role is provided, updates only members with that role.
    If NO role is provided, updates ALL members in the server (Use with caution).
    Usage: !updateall [@Role]
    """
    guild_config = get_guild_config(ctx.guild.id)
    
    members_to_update = []
    if role:
        role_id = str(role.id)
        if role_id not in guild_config.get("roles", {}):
            await ctx.send(f"Warning: Role **{role.name}** is not configured, but I will still enforce hierarchy/defaults for its members.")
        members_to_update = role.members
        await ctx.send(f"Starting batch update for **{len(members_to_update)}** users with role **{role.name}**...")
    else:
        members_to_update = ctx.guild.members
        await ctx.send(f"Starting batch update for **ALL {len(members_to_update)}** users in the server...")

    count = 0
    errors = 0
    
    # Pre-calculate known tags
    all_config_tags = list(guild_config.get("roles", {}).values())
    legacy_default_tags = ["[𝙼𝚂𝚄𝚊𝚗]", "[MSUAN]", "[Msuan]", "[msuan]"]
    default_tag = guild_config.get('default_tag')
    
    all_known_tags = list(set(all_config_tags + legacy_default_tags))
    if default_tag and default_tag not in all_known_tags:
        all_known_tags.append(default_tag)
        
    all_known_tags.sort(key=len, reverse=True)

    for member in members_to_update:
        try:
            # --- 1. Determine Target Tag (Hierarchy Check) ---
            user_configured_roles = [r for r in member.roles if str(r.id) in guild_config.get("roles", {})]
            user_configured_roles.sort(key=lambda r: r.position, reverse=True)
            
            target_tag = None
            if user_configured_roles:
                target_tag = guild_config["roles"][str(user_configured_roles[0].id)]
            else:
                target_tag = default_tag
            
            # --- 2. Clean Nickname ---
            current_nick = member.display_name
            temp_nick = current_nick
            
            for t in all_known_tags:
                if t in temp_nick:
                    new_val = temp_nick.replace(f" {t}", "")
                    if new_val == temp_nick:
                        new_val = temp_nick.replace(t, "")
                    temp_nick = new_val.strip()
            
            # --- 3. Append Target Tag ---
            if target_tag:
                final_nick = f"{temp_nick} {target_tag}"
            else:
                final_nick = temp_nick
                
            # --- 4. Length Check ---
            if len(final_nick) > 32:
                if target_tag:
                    allowed = 32 - len(target_tag) - 1
                    if allowed > 0:
                        final_nick = f"{temp_nick[:allowed].strip()} {target_tag}"
                    else:
                        final_nick = temp_nick[:32]
                else:
                    final_nick = temp_nick[:32]
            
            # --- 5. Apply ---
            if final_nick != current_nick:
                if member.id == ctx.guild.owner_id:
                    continue
                if member.top_role >= ctx.guild.me.top_role:
                    continue
                    
                await member.edit(nick=final_nick)
                count += 1
                print(f"Batch updated: {member.name} -> {final_nick}")
                
        except Exception as e:
            print(f"Failed to update {member.name}: {e}")
            errors += 1
            
    await ctx.send(f"**Batch Update Complete**\nUpdated: {count} users\nErrors/Skipped: {errors}")

@bot.command(name='removeall')
@commands.has_permissions(manage_nicknames=True)
async def remove_all_users(ctx, role: discord.Role):
    """
    Removes the configured tag from ALL users who have the specified role.
    This does NOT apply a new tag; it simply strips the role's tag.
    Usage: !removeall @Role
    """
    role_id = str(role.id)
    guild_config = get_guild_config(ctx.guild.id)
    
    if role_id not in guild_config.get("roles", {}):
        await ctx.send(f"Error: Role **{role.name}** is not configured with a tag. I don't know what to remove. Use `!stripall` if you want to remove a specific text.")
        return

    tag_to_remove = guild_config["roles"][role_id]
    await ctx.send(f"Starting batch removal of tag '**{tag_to_remove}**' for users with role **{role.name}**...")
    
    count = 0
    errors = 0
    
    for member in role.members:
        if not member.nick or tag_to_remove not in member.nick:
            continue
            
        # Permission checks
        if member.id == ctx.guild.owner_id:
             continue
        if member.top_role >= ctx.guild.me.top_role:
             continue

        # Remove the tag
        # Handle " {tag}" (with space) first
        new_nick = member.nick.replace(f" {tag_to_remove}", "")
        if new_nick == member.nick:
            # Handle "{tag}" (no space)
            new_nick = member.nick.replace(tag_to_remove, "")
            
        new_nick = new_nick.strip()
        
        try:
            await member.edit(nick=new_nick if new_nick else None)
            count += 1
            print(f"Removed tag from: {member.name}")
        except Exception as e:
            print(f"Failed to remove tag from {member.name}: {e}")
            errors += 1
            
    await ctx.send(f"**Batch Removal Complete**\nUpdated: {count} users\nErrors/Skipped: {errors}")

@bot.command(name='stripall')

@commands.has_permissions(manage_nicknames=True)
async def strip_all_users(ctx, role: discord.Role, tag_to_remove: str):
    """
    Removes a specific text/tag from the nicknames of ALL users with the specified role.
    Usage: !stripall @Role [TagToRemove]
    Example: !stripall @Member [𝙼𝚂𝚄𝚊𝚗]
    """
    await ctx.send(f"Starting batch removal of '**{tag_to_remove}**' for users with role **{role.name}**...")
    
    count = 0
    errors = 0
    
    for member in role.members:
        if not member.nick or tag_to_remove not in member.nick:
            continue
            
        # Permission checks
        if member.id == ctx.guild.owner_id:
             continue
        if member.top_role >= ctx.guild.me.top_role:
             continue

        # Remove the tag
        new_nick = member.nick.replace(f" {tag_to_remove}", "")
        if new_nick == member.nick:
            new_nick = member.nick.replace(tag_to_remove, "")
            
        new_nick = new_nick.strip()
        
        try:
            await member.edit(nick=new_nick if new_nick else None)
            count += 1
            print(f"Stripped tag from: {member.name}")
        except Exception as e:
            print(f"Failed to strip {member.name}: {e}")
            errors += 1
            
    await ctx.send(f"**Batch Strip Complete**\nUpdated: {count} users\nErrors/Skipped: {errors}")

@bot.event
async def on_member_join(member):
    """
    Triggered when a new member joins the server.
    Applies the default tag if configured.
    """
    guild_config = get_guild_config(member.guild.id)
    default_tag = guild_config.get('default_tag')
    
    # If no default tag is configured for this server, do nothing
    if not default_tag:
        return
        
    # New members typically have no roles, so we apply default_tag
    # Unless they are bots or have auto-roles assigned very quickly?
    # We'll just append default_tag to their name.
    
    current_nick = member.display_name
    
    # Check if they already have it (unlikely)
    if default_tag in current_nick:
        return
        
    final_nick = f"{current_nick} {default_tag}"
    
    # Length check
    if len(final_nick) > 32:
        allowed = 32 - len(default_tag) - 1
        if allowed > 0:
            final_nick = f"{current_nick[:allowed].strip()} {default_tag}"
        else:
            final_nick = current_nick[:32]
            
    try:
        await member.edit(nick=final_nick)
        print(f"Join Update: {member.name} -> {final_nick}")
    except Exception as e:
        print(f"Failed to update new member {member.name}: {e}")

@bot.event
async def on_member_update(before, after):
    """
    Triggered when a member updates (e.g., roles added/removed, or completes screening).
    """
    try:
        # Check for role changes OR pending status change (Member Screening completion)
        # We also want to check if the nickname changed (to enforce tags), 
        # but we must be careful not to loop.
        
        # Check if we need to process this update
        # We process if:
        # 1. Roles changed
        # 2. Pending status changed
        # 3. Nickname changed (to enforce tags)
        
        roles_changed = before.roles != after.roles
        pending_changed = before.pending != after.pending
        nick_changed = before.display_name != after.display_name
        
        if not (roles_changed or pending_changed or nick_changed):
            return

        # Specific check for Membership Screening Completion
        if before.pending and not after.pending:
            print(f"[INFO] Membership Screening Completed for {after.name} (Guild: {after.guild.name})")
            # Small delay to allow permissions/roles to settle
            await asyncio.sleep(1)

        print(f"[DEBUG] Member Update Processing: {after.name}")

        guild_config = get_guild_config(after.guild.id)
        current_nick = after.display_name
        
        # --- 1. Determine the Target Tag based on Hierarchy ---
        # Find all roles the user has that are in our config
        user_configured_roles = [r for r in after.roles if str(r.id) in guild_config.get("roles", {})]
        
        # Sort by position descending (Highest role first)
        user_configured_roles.sort(key=lambda r: r.position, reverse=True)
        
        # Determine the default tag (fallback)
        default_tag = guild_config.get('default_tag')

        target_tag = None
        if user_configured_roles:
            # User has configured roles, pick the highest one
            highest_role = user_configured_roles[0]
            target_tag = guild_config["roles"][str(highest_role.id)]
        else:
            # User has no configured roles, revert to default
            target_tag = default_tag

        # If neither role tag nor default tag is configured, we might want to strip any OLD tags
        # But if there's absolutely no config for this guild, we should probably do nothing
        if not target_tag and not guild_config.get("roles"):
             return

        # --- 2. Calculate New Nickname ---
        
        # List of all tags we know about (Configured + Defaults + Legacy)
        all_config_tags = list(guild_config.get("roles", {}).values())
        legacy_default_tags = ["[𝙼𝚂𝚄𝚊𝚗]", "[MSUAN]", "[Msuan]", "[msuan]"]
        
        # Use a set to avoid duplicates, but convert to list for sorting
        all_known_tags = list(set(all_config_tags + legacy_default_tags))
        if default_tag and default_tag not in all_known_tags:
            all_known_tags.append(default_tag)
        
        # We want to remove ANY known tag that is NOT our target_tag
        # (And also remove the target_tag temporarily to ensure it's placed correctly at the end)
        
        temp_nick = current_nick
        
        # Remove ALL known tags first to get the "clean" name
        # Sort by length descending to avoid partial replacements
        all_known_tags.sort(key=len, reverse=True)
        
        for tag in all_known_tags:
            if tag in temp_nick:
                # Try removing " {tag}" (with space)
                new_val = temp_nick.replace(f" {tag}", "")
                if new_val == temp_nick:
                    # Try removing "{tag}" (no space)
                    new_val = temp_nick.replace(tag, "")
                temp_nick = new_val.strip()
                
        # Now temp_nick should be just the username without any known tags
        
        # --- 3. Append Target Tag ---
        if target_tag:
            final_nick = f"{temp_nick} {target_tag}"
        else:
            final_nick = temp_nick

        # --- 4. Length Check (32 chars max) ---
        if len(final_nick) > 32:
            if target_tag:
                # Truncate name to fit tag
                allowed_len = 32 - len(target_tag) - 1 # -1 for space
                if allowed_len > 0:
                    final_nick = f"{temp_nick[:allowed_len].strip()} {target_tag}"
                else:
                    final_nick = temp_nick[:32] # Fallback
            else:
                final_nick = temp_nick[:32]

        # --- 5. Apply Changes ---
        if final_nick != current_nick:
            # Permission/Hierarchy Checks
            if after.id == after.guild.owner_id:
                return
            if after.top_role >= after.guild.me.top_role:
                print(f"[DEBUG] Cannot update {after.name}: User's top role is higher or equal to Bot's top role.")
                return

            try:
                await after.edit(nick=final_nick)
                print(f"[SUCCESS] Update: {after.name} -> {final_nick}")
            except discord.Forbidden:
                 print(f"[ERROR] Permission Denied: Cannot update {after.name}.")
            except Exception as e:
                print(f"[ERROR] Failed to update {after.name}: {e}")
                
    except Exception as e:
        print(f"[CRITICAL ERROR] in on_member_update: {e}")

@bot.event
async def on_command_error(ctx, error):
    """
    Handles command errors, specifically missing permissions.
    """
    if isinstance(error, commands.MissingPermissions):
        await ctx.send(f"⛔ **Access Denied**: You need the **Manage Nicknames** permission to use this command.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"⚠️ **Missing Argument**: {error}")
    elif isinstance(error, commands.BadArgument):
        await ctx.send(f"⚠️ **Bad Argument**: {error}")
    else:
        print(f"Command Error: {error}")
        # Optionally send generic error to chat?
        # await ctx.send(f"An error occurred: {error}")

if __name__ == "__main__":
    if not TOKEN:
        print("Error: DISCORD_TOKEN not found in environment variables.")
    else:
        keep_alive()  # Start the web server
        try:
            bot.run(TOKEN)
        except discord.errors.PrivilegedIntentsRequired:
            print("CRITICAL ERROR: Privileged Intents not enabled!")
            print("1. Go to Discord Developer Portal (https://discord.com/developers/applications)")
            print("2. Select your Bot -> Click 'Bot' tab")
            print("3. Scroll down to 'Privileged Gateway Intents'")
            print("4. ENABLE 'Server Members Intent' and 'Message Content Intent'")
            print("5. Save Changes and Restart.")
            import sys
            sys.exit(1)
        except Exception as e:
            print(f"FATAL ERROR: Bot crashed: {e}")
            # Ensure the process exits so the hosting platform knows it failed
            import sys
            sys.exit(1)
