## Local Development

For local development, you likely want to iterate using your own Github Apps (still owned by Noq org).
You can click on this [link](https://github.com/organizations/noqdev/settings/apps/new?name=noq-username&description=cloudumi-github-integration&url=https%3A%2F%2Fnoq.dev%2F&setup_url=https%3A%2F%2Fnoq-username.loca.lt%2Fapi%2Fv3%2Fgithub%2Fcallback%2F&webhook_active=true&webhook_url=https%3A%2F%2Fnoq-username.loca.lt%2Fapi%2Fv3%2Fgithub%2Fevents%2F&events[]=meta&events[]=issue_comment&events[]=pull_request_review&events[]=pull_request&events[]=push&public=true&contents=write&pull_requests=write&issues=write) to create your own GitHub App, you will have to modify the name of the app
because name is global across GitHub App and replace noq-username with noq-steven for example to match
your own local tunnel URL.
