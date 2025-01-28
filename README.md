# NPL AI Starter

This project aims to get you started with NPL AI orchestration. It has some minimal examples of:

- [A slackbot NPL connector](python/slack_connector)
- [A Teams bot NPL connector](python/teams_connector)
- [A simple agent worker that queries Bedrock or Azure OpenAI LLMs using langchain](python/agent_worker)
- How to consume NPL notifications for async processing
- How to generate and use an OpenAPI client using the generated NPL OpenAPI spec

The toy example provided is a simple chat where the user provides unstructured business requirements, and is provided
with a structured technical implementation ticket in response. A protocol is instantiated when the user sends a message,
and notifications are used to asynchronously process the user's message and respond with the ticket.

## Getting started

The .env.example files indicate which variables you will need to provide in order to run the examples. You can copy them
to .env files and fill in the blanks.

This project assumes that the NPL API is deployed to Noumena Cloud (a local Docker setup is possible, but somewhat more
complex, and is thus not covered here).

Once you have the NPL API running, you will need to configure the users (`slackbot`, `teamsbot`, `worker`) in the
Keycloak instance associated with your NPL application. Navigate to the Keycloak admin console, select the `noumena`
realm, and create the users. Make sure to set the password for each user.

Before running the Python application, set up your Python environment (e.g virtualenv) and install the requirements. You
can invoke the `install-requirements` `Make` target in order to generate the OpenAPI client and install it along with the
other requirements and the local packages:

```shell
make install-requirements
```

The agent worker application can then be run like so, provided that you've configured your .env file correctly (
including one of the LLM providers detailed further down):

```shell
python -m agent_worker.agent_worker_app
```

Then choose either the Slack or Teams connector to run:

```shell
python -m slack_connector.slack_connector_app
```

or

```shell
python -m teams_connector.teams_connector_app
```

See below for notes on what else is required to run each connector.

### Slack

- Make sure you have a Slack app with a bot user
- Install ngrok
- Make sure to point your app to your ngrok url in the Slack app settings

### Teams

- Install ngrok
- Install the Bot Framework Emulator

### Bedrock

Install the aws cli and configure it with your AWS access key.

### Azure OpenAI LLMs

Provide the endpoint and key in the .env file.
