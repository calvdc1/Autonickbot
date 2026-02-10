# Auto Nickname Bot

A Discord bot that automatically updates a user's nickname when they receive a specific role by appending a custom tag.

## Features

- **Auto Nickname**: Appends a configured tag to a user's nickname when they are assigned a specific role.
- **Multi-Server Support**: Configuration is isolated per server. Settings in one server do not affect others.
- **Membership Screening Support**: Automatically updates nicknames when a user completes the "apply to join" (rules acceptance) process.
- **Custom Configuration**: Use commands to link roles to specific nickname tags.

## Setup

1.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Configure Token**:
    - Open `.env` and set:
      ```
      DISCORD_TOKEN=your_token_here
      ```
    - Do not commit `.env` (already gitignored). On Render/Heroku, set `DISCORD_TOKEN` in service env vars.

3.  **Run the Bot**:
    ```bash
    python bot.py
    ```

## Commands

- `!autonick @Role [Tag]`
    - Associates a tag with a role.
    - Example: `!autonick @VIP [VIP]`
    - Result: If user "James" gets the VIP role, their name becomes "James [VIP]".

- `!defaultnick [Tag]`
    - Sets the default tag for users who do NOT have any configured roles.
    - Example: `!defaultnick [Member]`

- `!removenick @Role`
    - Removes the configuration for a role.

- `!updateall [@Role]`
    - Updates the nickname for ALL users.
    - If a role is provided, updates only members with that role.
    - If NO role is provided, updates ALL members in the server.

- `!removeall @Role`
    - Removes the configured tag from ALL users who have the specified role.
    - This does NOT apply a new tag; it simply strips the role's tag.

- `!stripall @Role [TagToRemove]`
    - Removes a specific text/tag from the nicknames of ALL users with the specified role.
    - Example: `!stripall @Member [OldTag]`

- `!settings`
    - Shows the current configuration for the server: default tag and role-tag mappings.
    - Useful to verify setup quickly.

## Permissions

The bot requires the **Manage Nicknames** permission to function correctly. Ensure the bot's role is higher in the hierarchy than the users it is trying to rename.

## Deployment

### Heroku
This project includes a `Procfile` for easy deployment on Heroku.
1. Create a new app on Heroku.
2. Connect your GitHub repository.
3. Set the `DISCORD_TOKEN` in Heroku's "Config Vars".
4. Deploy the branch.

### Render
This project includes a `render.yaml` for deployment on Render.
1. Create a new "Web Service" on Render.
2. Connect your GitHub repository.
3. Select "Python 3" as the environment.
4. Set the Build Command to `pip install -r requirements.txt`.
5. Set the Start Command to `python bot.py`.
6. Add an Environment Variable `DISCORD_TOKEN` with your bot token.
7. Optional: Set `PORT` if needed; defaults to 8080 for the keep-alive server.

**Current Deployment:** [https://kamenosko.onrender.com](https://kamenosko.onrender.com)

### Replit / Others
The bot includes a `keep_alive.py` script that runs a Flask web server. This allows you to use uptime monitoring services (like UptimeRobot) to keep the bot alive on platforms that sleep inactive projects.
- Ensure you set the `DISCORD_TOKEN` in your environment secrets.
