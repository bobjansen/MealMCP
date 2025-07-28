# Goal of this project

Manage meal planning and pantry management using an LLM for business logic.

# Datastore

The code should be data store agnostic but we will start out using sqlite.

The PantryManager class can be used to interface with the database.

# User interface

The app should be usable through the Claude Desktop client or through a Dash website that uses API calling.

# Internationalization

Internationalization is done using the Python i18n module. Currently English and Dutch are supported.

# Status

The project is written in Python and be managed using uv.

It includes a dash app and a MCP server. The data is stored in a sqlite database.