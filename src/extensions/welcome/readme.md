# Copyright (c) Communauté Les Frères Poulain
# SPDX-License-Identifier: MIT

# Welcome Extension

The Welcome extension automatically sends a welcome message when a new member joins a
Discord server. It is designed to be simple to configure and easy to use.

## Features

- Automatic welcome message on member join
- Configurable via slash commands
- Customizable message with variables
- Multi-language support
- Per-server configuration

## Usage

To use the Welcome extension, enable it in the configuration file and configure the
welcome message using the `/bienvenue` slash command.

The message will be sent automatically in the selected channel whenever a new member
joins the server.

## Commands

- `/bienvenue`  
  Configure the welcome message and select the channel.

- `/bienvenue_off`  
  Disable the welcome message for the server.

- `/bienvenue_vars`  
  Display the list of available variables with explanations and examples.

## Variables

The welcome message supports the following variables:

- `{user}`: Member display name (nickname if set)
- `{mention}`: Member mention
- `{username}`: Discord username
- `{server}`: Server name
- `{member_count}`: Total number of members
- `{created_at}`: Account creation date
- `{joined_at}`: Join date

## Configuration

Example configuration in `config.yml`:

```yaml
welcome:
  enabled: true
```
