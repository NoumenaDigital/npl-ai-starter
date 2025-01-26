# NPL AI Starter

This project aims to get you started with NPL AI orchestration. It has some minimal examples of:

- [A slackbot NPL connector](python/slack_connector)
- [A Teams bot NPL connector](python/teams_connector)
- [A simple agent worker that queries Bedrock or Azure OpenAI LLMs using langchain](python/agent_worker)
- How to consume NPL notifications for async processing
- How to generate and use an OpenAPI client using the generated NPL OpenAPI spec

## Getting started

The .env.example files indicate which variables you will need to provide in order to run the examples. You can copy them to .env files and fill in the blanks.

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
